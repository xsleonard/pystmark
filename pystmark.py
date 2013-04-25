# -*- coding: ascii -*-

'''
    pystmark
    --------

    Postmark API library built on :mod:`requests`

    :copyright: 2013, see AUTHORS for more details
    :license: MIT, see LICENSE for more details

    :TODO:
        Attachments
        Bounce handler
        Tests
'''

import requests
from collections import Mapping
from urlparse import urljoin

try:
    import simplejson as json
except ImportError:
    import json


__title__ = 'pystmark'
__version__ = '0.1'
__license__ = 'MIT'

# Constant defined in the Postmark docs:
#   http://developer.postmarkapp.com/developer-build.html
POSTMARK_API_URL = 'http://api.postmarkapp.com/'
POSTMARK_API_URL_SECURE = 'https://api.postmarkapp.com/'
POSTMARK_API_TEST_KEY = 'POSTMARK_API_TEST'
MAX_RECIPIENTS_PER_MESSAGE = 20
MAX_BATCH_MESSAGES = 500


class PystError(Exception):
    '''Base `Exception` for :mod:`pystmark` errors.'''
    message = ''

    def __init__(self, message=None):
        if message is not None:
            self.message = message

    def __str__(self):
        return str(self.message)


class PystMessageError(PystError):
    ''' Raised when a message meant to be sent to Postmark API looks
        malformed
    '''
    message = 'Refusing to send malformed message'


class PystResponseError(PystError):
    '''Base `Exception` for errors received from Postmark API'''

    def __init__(self, response, message=None):
        self.response = response
        try:
            self.data = response.json()
        except ValueError:
            self.data = {}
        self.error_code = self.data.get('ErrorCode')
        self.response_message = self.data.get('Message', '')
        super(PystResponseError, self).__init__(message=message)

    def __str__(self):
        if not self.data:
            msg = 'Not a valid JSON response. Status: {0}'
            return msg.format(self.response.status_code)
        msg = '[ErrorCode {0}, Message: "{1}"]'
        msg = msg.format(self.error_code, self.response_message)
        if self.message:
            msg = '{0} {1}'.format(self.message, msg)
        return msg


class PystUnauthorizedError(PystResponseError):
    '''Raised when Postmark responds with a :attr:`status_code` of 401
    Indicates a missing or incorrect API key.
    '''
    pass


class PystUnprocessableEntityError(PystResponseError):
    '''Raised when Postmark responds with a :attr:`status_code` of 422.
    Indicates message(s) received by Postmark were malformed.
    '''
    pass


class PystInternalServerError(PystResponseError):
    '''Raised when Postmark responds with a :attr:`status_code` of 500
    Indicates an error on Postmark's end. Any messages sent
    in the request were not received by them.
    '''
    pass


class PystResponse(object):
    '''Wrapper around :class:`requests.Response`.'''

    def __init__(self, response):
        self._requests_response = response

    def raise_for_status(self):
        '''Raise Postmark-specific error messages'''
        if self.status_code == 401:
            raise PystUnauthorizedError(self._requests_response)
        elif self.status_code == 422:
            raise PystUnprocessableEntityError(self._requests_response)
        elif self.status_code == 500:
            raise PystInternalServerError(self._requests_response)
        return self._requests_response.raise_for_status()

    def __getattribute__(self, k):
        if k == 'raise_for_status':
            return object.__getattribute__(self, 'raise_for_status')
        r = object.__getattribute__(self, '_requests_response')
        if k == '_requests_response':
            return r
        return r.__getattribute__(k)

    def __setattr__(self, k, v):
        if k == '_requests_response':
            object.__setattr__(self, k, v)
        else:
            self._requests_response.__setattr__(k, v)


class PystMessage(object):
    ''' A container for pystmark messages. '''

    _fields = {
        'to': 'To',
        'sender': 'From',
        'cc': 'Cc',
        'bcc': 'Bcc',
        'subject': 'Subject',
        'tag': 'Tag',
        'html': 'HtmlBody',
        'text': 'TextBody',
        'reply_to': 'ReplyTo',
        'headers': 'Headers'
    }

    _to = None
    _cc = None
    _bcc = None

    def __init__(self, sender=None, to=None, cc=None, bcc=None, subject=None,
                 tag=None, html=None, text=None, reply_to=None, headers=None,
                 verify=False):
        self.sender = sender
        self.to = to
        self.cc = cc
        self.bcc = bcc
        self.subject = subject
        self.tag = tag
        self.html = html
        self.text = text
        self.reply_to = reply_to
        self.headers = headers
        if verify:
            self.verify()

    def data(self):
        d = {}
        for val, key in self._fields.items():
            val = getattr(self, val)
            if val is not None:
                d[key] = val
        return d

    def json(self):
        return json.dumps(self.data(), ensure_ascii=False)

    @classmethod
    def load_message(self, message, **kwargs):
        kwargs.update(message)
        message = kwargs
        try:
            message = PystMessage(**message)
        except TypeError as e:
            message = self._convert_postmark_to_native(kwargs)
            if message:
                message = PystMessage(**message)
            else:
                raise e
        return message

    def verify(self):
        if self.to is None:
            raise PystMessageError('"to" is required')
        if self.html is None and self.text is None:
            err = 'At least one of "html" or "text" must be provided'
            raise PystMessageError(err)
        self._verify_headers()
        if (MAX_RECIPIENTS_PER_MESSAGE and
                len(self.recipients) > MAX_RECIPIENTS_PER_MESSAGE):
            err = 'No more than {0} recipients accepted.'
            raise PystMessageError(err.format(MAX_RECIPIENTS_PER_MESSAGE))

    @property
    def recipients(self):
        cc = self._cc or []
        bcc = self._bcc or []
        return self._to + cc + bcc

    @property
    def to(self):
        if self._to is not None:
            return ','.join(self._to)

    @to.setter
    def to(self, to):
        if isinstance(to, basestring):
            if ',' in to:
                to = to.split(',')
            else:
                to = [to]
        self._to = to

    @property
    def cc(self):
        if self._cc is not None:
            return ','.join(self._cc)

    @cc.setter
    def cc(self, cc):
        if isinstance(cc, basestring):
            if ',' in cc:
                cc = cc.split(',')
            else:
                cc = [cc]
        self._cc = cc

    @property
    def bcc(self):
        if self._bcc is not None:
            return ','.join(self._bcc)

    @bcc.setter
    def bcc(self, bcc):
        if isinstance(bcc, basestring):
            if ',' in bcc:
                bcc = bcc.split(',')
            else:
                bcc = [bcc]
        self._bcc = bcc

    @classmethod
    def _convert_postmark_to_native(cls, message):
        d = {}
        for dest, src in cls._fields.items():
            if src in message:
                d[dest] = message[src]
        return d

    def _verify_headers(self):
        if self.headers is None:
            return
        for header in self.headers:
            if not isinstance(header, Mapping):
                raise PystMessageError('Invalid "Header" value')
            required = set(('Name', 'Value'))
            for key in required:
                if key not in header:
                    err = 'Header item must contain "{0}"'
                    raise PystMessageError(err.format(key))
            if set(header) - required:
                err = 'Header item must contain only {0}'
                words = ['"{0}"'.format(r) for r in required]
                raise PystMessageError(err.format(' and '.join(words)))

    def __eq__(self, other):
        if isinstance(other, Mapping):
            other = self.__class__.load_message(other)
        return self.data() == other.data()

    def __ne__(self, other):
        return not self.__eq__(other)


class PystSender(object):
    '''A wrapper for the Postmark API.

    All of the arguments used in constructing this object are
    used as defaults in the final call to :meth:`Pystmark.send`.
    You can override any of them at that time.

    :param message: Default message data
    :type message: :keyword:`dict`
    :param api_key: Your Postmark API key.
    :param secure: Use the https scheme for Postmark API
    :param test: Make a test request to the Postmark API
    :param request_args: Passed to :func:`requests.post`
    :type request_args: :keyword:`dict`
    '''

    endpoint = '/email'
    _headers = {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
    }
    _api_key_header_name = 'X-Postmark-Server-Token'

    def __init__(self, message=None, api_key=None, secure=True,
                 test=False, request_args=None):
        self._load_initial_message(message)
        self.api_key = api_key
        self.secure = secure
        self.test = test
        if request_args is None:
            request_args = {}
        self.request_args = request_args

    def send(self, message=None, api_key=None, test=None,
             headers=None, secure=None, request_args=None):
        '''Send request to Postmark API.
        Returns result of :func:`requests.post`.

        :param message: Your Postmark message data.
        :type message: :keyword:`dict`
        :param api_key: Your Postmark API key.
        :type api_key: :keyword:`str`
        :param test: Make a test request to the Postmark API.
        :param headers: Headers to pass to :func:`requests.request`'
        :type headers: keyword:`dict`
        :param secure': Use the https Postmark API.
        :param request_args: Passed to :func:`requests.post`
        :type request_args: :keyword:`dict`
        :rtype: :class:`requests.Response`
        '''
        if request_args is None:
            request_args = {}
        self._merge_request_args(request_args)

        headers = self._get_headers(api_key=api_key, headers=headers,
                                    test=test)
        self._reverse_update(request_args.setdefault('headers', {}),
                             headers)
        del request_args['headers']

        data = self._get_request_content(message)
        self._reverse_update(request_args.setdefault('data', {}),
                             data)
        del request_args['data']

        url = self._get_api_url(secure=secure)
        response = requests.post(url, data=data, headers=headers,
                                 **request_args)
        response = PystResponse(response)
        return response

    def _load_initial_message(self, message=None):
        if message is None:
            message = PystMessage(verify=False)
        if isinstance(message, Mapping):
            message = PystMessage.load_message(message)
        self.message = message

    def _reverse_update(self, src, dest):
        '''Updates dest with values from src if key in src is not
        present in dest

        :param src: Data to use as defaults for dest.
        :type src: :keyword:`dict`.
        :param dest: Object to load defaults to.
        :type dest: :keyword:`dict`.
        :type message: :keyword:`dict`
        '''
        for k, v in src.iteritems():
            dest.setdefault(k, v)

    def _merge_request_args(self, request_args):
        '''Merges request_args to be passed to :func:`requests.request`
        Since request_args possibly contains :keyword:`dict`s itself,
        we need to :meth:`_reverse_update` these.

        :param request_args: request_args mapping to be updated
        :type request_args: :keyword:`dict`
        '''
        for k, v in self.request_args.iteritems():
            if isinstance(v, Mapping):
                d = request_args.get(k, {})
                if not isinstance(d, Mapping):
                    msg = ('Default request_args "{0}" does not match '
                           'provided request_args')
                    raise ValueError(msg.format(k))
                self._reverse_update(v, d)
                request_args[k] = d
            else:
                request_args.setdefault(k, v)

    def _cast_message(self, message=None):
        if message is None:
            message = {}
        if isinstance(message, Mapping):
            message = PystMessage.load_message(message)
        message = message.data()
        self._reverse_update(self.message.data(), message)
        return PystMessage.load_message(message, verify=True)

    def _get_request_content(self, message=None):
        '''Updates message with default message paramaters.

        :param message: Postmark message data
        :type message: :keyword:`dict`
        :rtype: JSON encoded :keyword:`unicode`
        '''
        message = self._cast_message(message=message)
        return message.json()

    def _get_api_url(self, secure=None):
        '''Constructs Postmark API url

        :param secure': Use the https Postmark API.
        :rtype: Postmark API url
        '''
        if secure is None:
            secure = self.secure
        if secure:
            api_url = POSTMARK_API_URL_SECURE
        else:
            api_url = POSTMARK_API_URL
        return urljoin(api_url, self.endpoint)

    def _get_headers(self, api_key=None, headers=None, test=None):
        if headers is None:
            headers = {}
        if (test is None and self.test) or test:
            headers[self._api_key_header_name] = POSTMARK_API_TEST_KEY
        elif api_key is not None:
            headers[self._api_key_header_name] = api_key
        headers.update(self._headers)
        if not headers.get(self._api_key_header_name):
            raise ValueError('Postmark API Key not provided')
        return headers


class PystBatchSender(PystSender):
    '''A wrapper for the Postmark Batch API.

    All of the arguments used in constructing this object are
    used as defaults in the final call to :meth:`Pystmark.send`.
    You can override any of them at that time.

    :param message: Default message data
    :type message: :keyword:`dict`
    :param api_key: Your Postmark API key.
    :param secure: Use the https scheme for Postmark API
    :param test: Make a test request to the Postmark API
    :param request_args: Passed to :func:`requests.post`
    :type request_args: :keyword:`dict`
    '''

    endpoint = '/email/batch'

    def send(self, message=None, api_key=None, test=None,
             secure=None, request_args=None):
        '''Send batch request to Postmark API.
        Returns result of :func:`requests.post`.

        :param message: Your Postmark message data.
        :type message: A collection of Postmark message data
        :param api_key: Your Postmark API key.
        :type api_key: :keyword:`str`
        :param test: Make a test request to the Postmark API.
        :param secure': Use the https Postmark API.
        :param request_args: Passed to :func:`requests.post`
        :type request_args: :keyword:`dict`
        :rtype: :class:`requests.Response`
        '''
        return super(PystBatchSender, self).send(message=message, test=test,
                                                 api_key=api_key,
                                                 secure=secure,
                                                 request_args=request_args)

    def _get_request_content(self, message=None):
        '''Updates all messages in message with default message
        parameters.

        :param message: A collection of Postmark message data
        :type message: a collection of message :keyword:`dict`s
        :rtype: JSON encoded :keyword:`unicode`
        '''
        if not message:
            raise PystMessageError('No messages to send.')
        if len(message) > MAX_BATCH_MESSAGES:
            err = 'Maximum {0} messages allowed in batch'
            raise PystMessageError(err.format(MAX_BATCH_MESSAGES))
        message = [self._cast_message(message=msg) for msg in message]
        message = [msg.data() for msg in message]
        return json.dumps(message, ensure_ascii=False)


class PystBounceHandler(object):
    pass
