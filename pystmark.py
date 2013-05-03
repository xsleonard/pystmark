# -*- coding: ascii -*-

'''
    pystmark
    --------

    Postmark API library built on :mod:`requests`

    :copyright: 2013, see AUTHORS for more details
    :license: MIT, see LICENSE for more details

    :TODO:
        Live/Integration tests

        Support for bounce and inbound hooks? These should be mostly handled
        in a framework specific manner but there might be some common utilities
        to provide.
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

bounce_types = {
    'HardBounce': 1,
    'Transient': 2,
    'Unsubscribe': 16,
    'Subscribe': 32,
    'AutoResponder': 64,
    'AddressChange': 128,
    'DnsError': 256,
    'SpamNotification': 512,
    'OpenRelayTest': 1024,
    'Unknown': 2048,
    'SoftBounce': 4096,
    'VirusNotification': 8192,
    'ChallengeVerification': 16384,
    'BadEmailAddress': 100000,
    'SpamComplaint': 100001,
    'ManuallyDeactivated': 100002,
    'Unconfirmed': 100003,
    'Blocked': 100006,
    'SMTPApiError': 100007,
    'InboundError': 100008
}


''' Simple API '''


def send(message, **kwargs):
    return _default_pyst_sender.send(message=message, **kwargs)


def send_batch(messages, **kwargs):
    return _default_pyst_batch_sender.send(message=messages, **kwargs)


def get_delivery_stats(**kwargs):
    return _default_delivery_stats.get(**kwargs)


def get_bounces(**kwargs):
    return _default_bounces.get(**kwargs)


def get_bounce(bounce_id, **kwargs):
    return _default_bounce.get(bounce_id, **kwargs)


def get_bounce_dump(bounce_id, **kwargs):
    return _default_bounce_dump.get(bounce_id, **kwargs)


def get_bounce_tags(**kwargs):
    return _default_bounce_tags.get(**kwargs)


def activate_bounce(bounce_id, **kwargs):
    return _default_bounce_activate.activate(bounce_id, **kwargs)


''' Messages '''


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


class PystBouncedMessage(object):

    def __init__(self, bounce_data):
        self._data = bounce_data
        self.id = bounce_data['ID']
        self.type = bounce_data['Type']
        self.message_id = bounce_data['MessageID']
        self.type_code = bounce_data['TypeCode']
        self.details = bounce_data['Details']
        self.email = bounce_data['Email']
        self.bounced_at = bounce_data['BouncedAt']
        self.dump_available = bounce_data['DumpAvailable']
        self.inactive = bounce_data['Inactive']
        self.can_activate = bounce_data['CanActivate']
        self.content = bounce_data.get('Content')
        self.subject = bounce_data['Subject']

    def dump(self, **kwargs):
        return _default_bounce_dump.get(self.id, **kwargs)


class PystBounceType(object):

    def __init__(self, bounce_type):
        self.count = bounce_type.get('Count', 0)
        self.name = bounce_type['Name']
        self.type = bounce_type.get('Type', 'All')


''' Response Wrappers '''


class PystResponse(object):

    _attrs = []

    def __init__(self, response):
        self._attrs.append('_data')
        try:
            self._data = response.json()
        except ValueError:
            self._data = None
        self._requests_response = response

    def __getattribute__(self, k):
        if k == '_attrs' or k in object.__getattribute__(self, '_attrs'):
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


class PystBouncesResponse(PystResponse):

    _attrs = ['bounces', 'total']

    def __init__(self, response):
        super(PystBouncesResponse, self).__init__(response)
        data = self._data or {}
        self.total = data.get('TotalCount', 0)
        bounces = data.get('Bounces', [])
        self.bounces = [PystBouncedMessage(bounce) for bounce in bounces]


class PystBounceResponse(PystResponse):

    _attrs = ['bounce']

    def __init__(self, response):
        super(PystBounceResponse, self).__init__(response)
        if self._data is None:
            self.bounce = None
        else:
            self.bounce = PystBouncedMessage(self._data)


class PystBounceDumpResponse(PystResponse):

    def __init__(self, response):
        super(PystBounceDumpResponse, self).__init__(response)
        data = self._data or {}
        self.dump = data.get('Body')


class PystBounceTagsResponse(PystResponse):

    def __init__(self, response):
        super(PystBounceTagsResponse, self).__init__(response)
        self.tags = self._data or []


class PystDeliveryStatsResponse(PystResponse):

    def __init__(self, response):
        super(PystDeliveryStatsResponse, self).__init__(response)
        data = self._data or {}
        self.inactive = data.get('InactiveMails', 0)
        self.total = 0
        bounces = data.get('Bounces', [])
        self.bounces = {}
        for bounce in bounces:
            bounce = PystBounceType(bounce)
            self.bounces[bounce.type] = bounce
            if bounce.type == 'All':
                self.total = bounce.count


class PystBounceActivateResponse(PystResponse):

    def __init__(self, response):
        super(PystBounceActivateResponse, self).__init__(response)
        data = self._data or {}
        self.message = data.get('Message', '')
        bounce = data.get('Bounce')
        if bounce is None:
            self.bounce = None
        else:
            self.bounce = PystBouncedMessage(data['Bounce'])


''' Interfaces '''


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

    def get(self, secure=None, test=None, api_key=None, **request_args):
        url = self._get_api_url(secure=secure)
        headers = request_args.pop('headers', {})
        headers = self._get_headers(api_key=api_key, headers=headers,
                                    test=test)
        return self.request(url, headers=headers, **request_args)


''' Send API '''


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
                 **request_args):
        super(PystSender, self).__init__(api_key=api_key, secure=secure,
                                         test=test)
        self._load_initial_message(message)
        self.request_args = request_args

    def send(self, message=None, api_key=None, secure=None, test=None,
             **request_args):
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

    def send(self, message=None, api_key=None, secure=None, test=None,
             **request_args):
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


''' Bounce API '''


class PystBounces(PystGetInterface):
    endpoint = '/bounces'
    response_class = PystBouncesResponse

    def __init__(self, api_key=None, secure=True, test=False):
        super(PystBounces, self).__init__(api_key=api_key, secure=secure,
                                          test=test)
        self._last_response = None

    def request(self, url, **kwargs):
        response = super(PystBounces, self).request(url, **kwargs)
        self._last_response = response
        return response

    def _construct_params(self, bounce_type=None, inactive=None,
                          email_filter=None, message_id=None, count=None,
                          offset=None):
        params = {}
        if bounce_type is not None:
            if bounce_type not in bounce_types:
                err = 'Invalid bounce type "{0}".'
                raise PystBounceError(err.format(bounce_type))
            else:
                params['type'] = bounce_type
        if inactive is not None:
            params['inactive'] = inactive
        if email_filter is not None:
            params['emailFilter'] = email_filter
        if message_id is None:
            # If the message_id is given, count and offset are not
            # required, so we postpone assigning defaults to here
            if count is None:
                count = 25
            if offset is None:
                offset = 0
        else:
            params['messageID'] = message_id
        if count is not None:
            params['count'] = count
        if offset is not None:
            params['offset'] = offset
        return params

    def get(self, bounce_type=None, inactive=None, email_filter=None,
            message_id=None, count=None, offset=None, api_key=None,
            secure=None, test=None, params=None, **request_args):
        params = self._construct_params(bounce_type=bounce_type,
                                        inactive=inactive,
                                        email_filter=email_filter,
                                        message_id=message_id,
                                        count=count,
                                        offset=offset)
        url = self._get_api_url(secure=secure)
        headers = request_args.pop('headers', {})
        headers = self._get_headers(api_key=api_key, headers=headers,
                                    test=test)
        response = self.request(url, headers=headers, params=params,
                                **request_args)
        return response


class PystBounce(PystGetInterface):
    endpoint = '/bounces/{bounce_id}'
    response_class = PystBounceResponse

    def __init__(self, bounce_id=None, api_key=None, secure=True, test=False):
        super(PystBounce, self).__init__(api_key=api_key, secure=secure,
                                         test=test)
        self.bounce_id = bounce_id

    def get(self, bounce_id=None, api_key=None, secure=None, test=None,
            **request_args):
        if bounce_id is None:
            bounce_id = self.bounce_id
        if bounce_id is None:
            raise PystBounceError('bounce_id is required.')
        url = self._get_api_url(secure=secure, bounce_id=bounce_id)
        headers = request_args.pop('headers', {})
        headers = self._get_headers(api_key=api_key, headers=headers,
                                    test=test)
        return self.request(url, headers=headers, **request_args)


class PystBounceDump(PystBounce):
    response_class = PystBounceDumpResponse
    endpoint = '/bounces/{bounce_id}/dump'


class PystBounceTags(PystGetInterface):
    response_class = PystBounceTagsResponse
    endpoint = '/bounces/tags'


class PystDeliveryStats(PystGetInterface):
    response_class = PystDeliveryStatsResponse
    endpoint = '/deliverystats'


class PystBounceActivate(PystInterface):
    response_class = PystBounceActivateResponse
    method = 'PUT'
    endpoint = '/bounces/{bounce_id}/activate'

    def __init__(self, bounce_id=None, api_key=None, secure=True, test=False):
        super(PystBounceActivate, self).__init__(api_key=api_key,
                                                 secure=secure, test=test)
        self.bounce_id = bounce_id

    def activate(self, bounce_id=None, api_key=None, secure=None, test=None,
                 **request_args):
        if bounce_id is None:
            bounce_id = self.bounce_id
        if bounce_id is None:
            raise PystBounceError('bounce_id is required.')
        url = self._get_api_url(secure=secure, bounce_id=bounce_id)
        headers = request_args.pop('headers', {})
        headers = self._get_headers(api_key=api_key, headers=headers,
                                    test=test)
        return self.request(url, headers=headers, **request_args)


''' Exceptions '''


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


class PystBounceError(PystError):
    ''' Raised when a bounce API method fails '''
    message = 'Bounce API failure'


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
        msg = '{1} [ErrorCode {0}]'
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


''' Singletons '''

_default_pyst_sender = PystSender()
_default_pyst_batch_sender = PystBatchSender()
_default_bounces = PystBounces()
_default_bounce = PystBounce()
_default_bounce_dump = PystBounceDump()
_default_bounce_tags = PystBounceTags()
_default_delivery_stats = PystDeliveryStats()
_default_bounce_activate = PystBounceActivate()
