# -*- coding: ascii -*-

"""
    pystmark
    --------

    Postmark API library built on Python Requests

    :copyright: 2013, see AUTHORS for more details
    :license: MIT, see LICENSE for more details

    :TODO:
        Attachments
        Bounce handler
        Tests/PEP8/pyflakes
"""

import requests
from urlparse import urljoin

try:
    import simplejson as json
except ImportError:
    import json


__title__ = 'pystmark'
__version__ = '0.1'
__license__ = 'MIT'

_POSTMARK_API = 'http://api.postmarkapp.com/'
_POSTMARK_API_SECURE = 'https://api.postmarkapp.com/'


class PystError(Exception):

    def __init__(self, request, response):
        self.request = request
        self.response = response

    def __str__(self):
        return self.message


class PystUnauthorizedError(Exception):

    message = "Missing or incorrect API Key header."


class PystUnprocessableEntityError(Exception):

    def __init__(self, request, response):
        super(PystUnprocessableEntityError, self).__init__(request,
                                                           response)
        data = response.json()
        self.error_code = data.get("ErrorCode")
        self.message = data.get("Message", "")

    def __str__(self):
        return "{0} [ErrorCode {1}]".format(self.message,
                                             self.error_code)


class PystInternalServerError(Exception):

    message = "Postmark Internal Server Error. {0} message{1} lost"

    def __str__(self):
        ct = len(self.request.messages)
        s = 's' if ct > 1 else ''
        return self.message.format(ct, s)


class PystResponse(requests.Response):

    def _set_pyst_request(self, request):
        self._pyst_request = request

    def raise_on_status(self):
        if self.status_code == 401:
            raise PystUnauthorizedError(self.request, self)
        elif self.status_code == 422:
            raise PystUnprocessableEntityError(self.request, self)
        elif self.status_code == 500:
            raise PystInternalServerError(self.request, self)
        return super(PystResponse, self).raise_on_status()


class PystRequest(object):
    _endpoint = '/email'
    _headers = {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        }
    _api_key_header_name = 'X-Postmark-Server-Token'

    def __init__(self, api_key=None, secure=True, test=False,
                 **sender_options):
        if api_key is None:
            raise ValueError('Postmark API Key not provided')
        self.api_key = api_key
        self._headers[self._api_key_header_name] = self.api_key
        self.secure = secure
        self.test = test
        self.sender_options = sender_options

    def get_payload(self):
        return json.dumps(self.sender_options)

    def get_api_url(self):
        api_url = _POSTMARK_API
        if self.secure:
            api_url = _POSTMARK_API_SECURE
        return urljoin(api_url, self._endpoint)

    def send(self):
        url = self.get_api_url()
        data = self.get_payload()
        if self.test:
            return dict(url=url, data=data, headers=self._headers)
        return requests.post(url, data=data, headers=self._headers)


class PystBatchRequest(PystRequest):
    _endpoint = '/email/batch'

    def __init__(self, api_key=None, secure=True, test=False,
                 messages=None):
        if messages is None:
            raise ValueError("No messages provided")
        super(PystBatchRequest, self).__init__(api_key=api_key,
                                               secure=secure, test=test)
        self.messages = messages

    def get_payload(self):
        return json.dumps(self.messages)


class PystSender(object):
    _request_cls = PystRequest

    def __init__(self, api_key=None, secure=True, test=False,
                 **sender_options):
        self.api_key = api_key
        self.secure = secure
        self.test = test
        self.sender_options = sender_options

    def _fill_message_defaults(self, msg):
        for k, v in self.sender_options:
            msg.setdefault(k, v)

    def _apply_presets(self, to):
        to.setdefault('secure', self.secure)
        to.setdefault('api_key', self.api_key)
        to.setdefault('test', self.test)

    def create_request(self, **kwargs):
        self._apply_presets(kwargs)
        self._fill_message_defaults(kwargs)
        req = self._request_cls(**kwargs)
        return req

    def send(self, **kwargs):
        req = self.create_request(**kwargs)
        return req.send()


class PystBatchSender(PystSender):
    _request_cls = PystBatchRequest

    def __init__(self, api_key=None, secure=True, test=False,
                 **sender_options):
        super(PystBatchRequest, self).__init__(api_key=api_key,
                                               secure=secure, test=test,
                                               **sender_options)

    def _fill_message_defaults(self, to):
        messages = to['messages']
        if messages is None:
            return
        map(super(PystBatchRequest, self)._fill_message_defaults,
            messages)

    def create_request(self, messages=None, **kwargs):
        kwargs['messages'] = messages
        super(PystBatchRequest, self).create_request(**kwargs)


class PystBounceHandler(object):
    pass
