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
        Live/Integration Tests
'''

import requests
import mimetypes
import os.path
from collections import Mapping
from urlparse import urljoin
from base64 import b64encode

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
        self.error_code = self.data.get('ErrorCode', -1)
        self.message = self.data.get('Message', '')
        self.message_id = self.data.get('MessageID', '')
        self.submitted_at = self.data.get('SubmittedAt', '')
        self.to = self.data.get('To', '')
        super(PystResponseError, self).__init__(message=message)

    def __str__(self):
        if not self.data:
            msg = 'Not a valid JSON response. Status: {0}'
            return msg.format(self.response.status_code)
        msg = '[ErrorCode {0}, Message: "{1}"]'
        return msg.format(self.error_code, self.message)


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

    _attrs = []

    def __init__(self, response):
        self._requests_response = response

    def __getattribute__(self, k):
        if k in object.__getattribute__(self, '_attrs'):
            return object.__getattribute__(self, k)
        r = object.__getattribute__(self, '_requests_response')
        if k == '_requests_response':
            return r
        return r.__getattribute__(k)

    def __setattr__(self, k, v):
        if k == '_requests_response' or k in self._attrs:
            object.__setattr__(self, k, v)
        else:
            self._requests_response.__setattr__(k, v)


class PystSendResponse(PystResponse):
    '''Wrapper around :class:`requests.Response`.'''

    _attrs = ['raise_for_status']

    def raise_for_status(self):
        '''Raise Postmark-specific error messages'''
        if self.status_code == 401:
            raise PystUnauthorizedError(self._requests_response)
        elif self.status_code == 422:
            raise PystUnprocessableEntityError(self._requests_response)
        elif self.status_code == 500:
            raise PystInternalServerError(self._requests_response)
        return self._requests_response.raise_for_status()


class PystBounceResponse(PystResponse):
    pass


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
        'headers': 'Headers',
        '_attachments': 'Attachments',
    }

    _allowed_extensions = ['gif', 'jpeg', 'png', 'swf', 'dcr', 'tiff', 'bmp',
                           'ico', 'page-icon', 'wav', 'mp3', 'flv', 'avi',
                           'mpg', 'wmv', 'rm', 'mov', '3gp', 'mp4', 'm4a',
                           'ogv', 'txt', 'rtf', 'html', 'xml', 'ics', 'pdf',
                           'log', 'csv', 'docx', 'dotx', 'pptx', 'xlsx', 'odt',
                           'psd', 'ai', 'vcf', 'mobi', 'epub', 'pgp', 'ods',
                           'wps', 'pages', 'prn', 'eps', 'license', 'zip',
                           'dcm', 'enc', 'cdr', 'css', 'pst', 'mobileconfig',
                           'eml', 'gpx', 'kml', 'kmz', 'msl', 'rb', 'js',
                           'java', 'c', 'cpp', 'py', 'php', 'fl', 'jar', 'ttf',
                           'vpv', 'iif', 'timo', 'autorit', 'cathodelicense',
                           'itn', 'freshroute']

    _to = None
    _cc = None
    _bcc = None
    _default_content_type = 'application/octet-stream'

    def __init__(self, sender=None, to=None, cc=None, bcc=None, subject=None,
                 tag=None, html=None, text=None, reply_to=None, headers=None,
                 attachments=None, verify=False):
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
        self._attachments = attachments
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

    def attach_binary(self, data, filename, content_type=None):
        if self._attachments is None:
            self._attachments = []
        if content_type is None:
            content_type = self._detect_content_type(filename)
        attachment = {
            'Name': filename,
            'Content': b64encode(data),
            'ContentType': content_type
        }
        self._attachments.append(attachment)

    def attach_file(self, filename):
        # Open the file, grab the filename, detect content type
        name = os.path.basename(filename)
        if not name:
            err = 'Filename not found in path: {0}'
            raise PystMessageError(err.format(filename))
        with open(filename, 'rb') as f:
            data = f.read()
        self.attach_binary(data, name)

    def verify(self):
        if self.to is None:
            raise PystMessageError('"to" is required')
        if self.html is None and self.text is None:
            err = 'At least one of "html" or "text" must be provided'
            raise PystMessageError(err)
        self._verify_headers()
        self._verify_attachments()
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

    def _detect_content_type(self, filename):
        name, ext = os.path.splitext(filename)
        if not ext:
            raise PystMessageError('File requires an extension.')
        ext = ext.lower()
        if ext.lstrip('.') not in self._allowed_extensions:
            err = 'Extension "{0}" is not allowed.'
            raise PystMessageError(err.format(ext))
        if not mimetypes.inited:
            mimetypes.init()
        try:
            mimetype = mimetypes.types_map[ext]
        except KeyError:
            mimetype = self._default_content_type
        return mimetype

    def _verify_headers(self):
        if self.headers is None:
            return
        self._verify_dict_list(self.headers, ('Name', 'Value'), 'Header')

    def _verify_attachments(self):
        if self._attachments is None:
            return
        keys = ('Name', 'Content', 'ContentType')
        self._verify_dict_list(self._attachments, keys, 'Attachment')

    def _verify_dict_list(self, values, keys, name):
        keys = set(keys)
        name = name.title()
        for value in values:
            if not isinstance(value, Mapping):
                raise PystMessageError('Invalid {0} value'.format(name))
            for key in keys:
                if key not in value:
                    err = '{0} must contain "{1}"'
                    raise PystMessageError(err.format(name, key))
            if set(value) - keys:
                err = '{0} must contain only {1}'
                words = ['"{0}"'.format(r) for r in keys]
                words = ' and '.join(words)
                raise PystMessageError(err.format(name, words))

    def __eq__(self, other):
        if isinstance(other, Mapping):
            other = self.__class__.load_message(other)
        return self.data() == other.data()

    def __ne__(self, other):
        return not self.__eq__(other)


class PystInterface(object):

    method = None
    endpoint = None
    response_class = PystResponse

    _headers = {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
    }
    _api_key_header_name = 'X-Postmark-Server-Token'

    def __init__(self, api_key=None, secure=True, test=False):
        self.api_key = api_key
        self.secure = secure
        self.test = test

    def _get_api_url(self, secure=None, **formatters):
        '''Constructs Postmark API url

        :param secure': Use the https Postmark API.
        :rtype: Postmark API url
        '''
        if self.endpoint is None:
            raise NotImplementedError('endpoint must be defined on a subclass')
        if secure is None:
            secure = self.secure
        if secure:
            api_url = POSTMARK_API_URL_SECURE
        else:
            api_url = POSTMARK_API_URL
        url = urljoin(api_url, self.endpoint)
        if formatters:
            url = url.format(**formatters)
        return url

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

    def request(self, url, **kwargs):
        if self.method is None:
            raise NotImplementedError('method must be defined on a subclass')
        response = requests.request(self.method, url, **kwargs)
        return self.response_class(response)


class PystGetInterface(PystInterface):

    method = 'GET'

    def get(self, secure=None, test=None, api_key=None, request_args=None):
        url = self._get_api_url(secure=secure)
        headers = request_args.pop('headers', {})
        headers = self._get_headers(api_key=api_key, headers=headers,
                                    test=test)
        return self.request(url, headers=headers, **request_args)


class PystSender(PystInterface):
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

    method = 'POST'
    endpoint = '/email'
    response_class = PystSendResponse

    def __init__(self, message=None, api_key=None, secure=True, test=False,
                 request_args=None):
        super(PystSender, self).__init__(api_key=api_key, secure=secure,
                                         test=test)
        self._load_initial_message(message)
        if request_args is None:
            request_args = {}
        self.request_args = request_args

    def send(self, message=None, api_key=None, test=None, secure=None,
             request_args=None):
        '''Send request to Postmark API.
        Returns result of :func:`requests.post`.

        :param message: Your Postmark message data.
        :type message: :keyword:`dict`
        :param api_key: Your Postmark API key.
        :type api_key: :keyword:`str`
        :param test: Make a test request to the Postmark API.
        :param secure': Use the https Postmark API.
        :param request_args: Passed to :func:`requests.post`
        :type request_args: :keyword:`dict`
        :rtype: :class:`requests.Response`
        '''
        if request_args is None:
            request_args = {}
        self._merge_request_args(request_args)
        headers = request_args.pop('headers', {})
        headers = self._get_headers(api_key=api_key, headers=headers,
                                    test=test)
        data = self._get_request_content(message)
        url = self._get_api_url(secure=secure)
        return self.request(url, data=data, headers=headers, **request_args)

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

    def send(self, message=None, api_key=None, test=None, secure=None,
             request_args=None):
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


class PystBounces(PystGetInterface):
    endpoint = '/bounces'

    def get(self, secure=None, params=None, test=None, api_key=None,
            request_args=None):
        # TODO -- update params
        url = self._get_api_url(secure=secure)
        headers = request_args.pop('headers', {})
        headers = self._get_headers(api_key=api_key, headers=headers,
                                    test=test)
        return self.request(url, headers=headers, params=params,
                            **request_args)


class PystBounce(PystGetInterface):
    endpoint = '/bounces/{bounce_id}'
    response_class = PystBounceResponse

    def get(self, bounce_id, secure=None, test=None, api_key=None,
            request_args=None):
        url = self._get_api_url(secure=secure, bounce_id=bounce_id)
        headers = request_args.pop('headers', {})
        headers = self._get_headers(api_key=api_key, headers=headers,
                                    test=test)
        return self.request(url, headers=headers, **request_args)


class PystBounceDump(PystBounce):
    endpoint = '/bounces/{bounce_id}/dump'


class PystBounceTags(PystGetInterface):
    endpoint = '/bounces/tags'


class PystDeliveryStats(PystGetInterface):
    endpoint = '/deliverystats'


class PystBounceActivate(PystInterface):
    method = 'PUT'
    endpoint = '/bounces/{bounce_id}/activate'

    def activate(self, bounce_id, secure=None, test=None, api_key=None,
                 request_args=None):
        url = self._get_api_url(secure=secure, bounce_id=bounce_id)
        headers = request_args.pop('headers', {})
        headers = self._get_headers(api_key=api_key, headers=headers,
                                    test=test)
        return self.request(url, headers=headers, **request_args)


_default_pyst_sender = PystSender()
_default_pyst_batch_sender = PystBatchSender()
_default_bounces = PystBounces()
_default_bounce = PystBounce()
_default_bounce_dump = PystBounceDump()
_default_bounce_tags = PystBounceTags()
_default_delivery_stats = PystDeliveryStats()
_default_bounce_activate = PystBounceActivate()


def send(api_key, message, **kwargs):
    return _default_pyst_sender.send(message=message, api_key=api_key,
                                     **kwargs)


def send_batch(api_key, messages, **kwargs):
    return _default_pyst_batch_sender.send(message=messages, api_key=api_key,
                                           **kwargs)


def get_delivery_stats(api_key, **kwargs):
    return _default_delivery_stats.get(api_key=api_key, **kwargs)


def get_bounces(api_key, **kwargs):
    return _default_bounces.get(api_key=api_key, **kwargs)


def get_bounce(api_key, bounce_id, **kwargs):
    return _default_bounce.get(bounce_id, api_key=api_key, **kwargs)


def get_bounce_dump(api_key, bounce_id, **kwargs):
    return _default_bounce_dump.get(bounce_id, api_key=api_key, **kwargs)


def get_bounce_tags(api_key, **kwargs):
    return _default_bounce_tags.get(**kwargs)


def activate_bounce(api_key, bounce_id, **kwargs):
    return _default_bounce_activate.activate(bounce_id, api_key=api_key,
                                             **kwargs)
