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
        Merge Requests into Mail
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
    """Base `Exception` for pystmark errors."""
    message = ''

    def __init__(self, request, response):
        self.request = request
        self.response = response

    def __str__(self):
        return str(self.message)


class PystUnauthorizedError(Exception):
    """Thrown when Postmark responds with a `status_code` of 401
    Indicates a missing or incorrect API key.
    """
    message = "Missing or incorrect API Key header."


class PystUnprocessableEntityError(Exception):
    """Thrown when Postmark responds with a `status_code` of 422.
    Indicates message(s) received by Postmark were malformed.
    """
    def __init__(self, request, response):
        super(PystUnprocessableEntityError, self).__init__(request,
                                                           response)
        data = response.json()
        self.error_code = data.get("ErrorCode")
        self.message = data.get("Message", "")

    def __str__(self):
        msg = "{0} [ErrorCode {1}]"
        return msg.format(self.message, self.error_code)


class PystInternalServerError(Exception):
    """Thrown when Postmark responds with a `status_code` of 500
    Indicates an error on Postmark's end. Any messages sent
    in the request were not received by them.
    """
    message = "Postmark Internal Server Error. {0} message{1} lost"

    def __str__(self):
        ct = len(self.request.messages)
        s = 's' if ct > 1 else ''
        return self.message.format(ct, s)


class PystResponse(requests.Response):
    """Wrapper around `requests.Response`. Overrides
    `requests.Response.raise_on_status` to give Postmark-specific
    error messages
    """

    def raise_on_status(self):
        if self.status_code == 401:
            raise PystUnauthorizedError(self.request, self)
        elif self.status_code == 422:
            raise PystUnprocessableEntityError(self.request, self)
        elif self.status_code == 500:
            raise PystInternalServerError(self.request, self)
        return super(PystResponse, self).raise_on_status()


class PystSender(object):
    _endpoint = '/email'
    _headers = {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
    }
    _api_key_header_name = 'X-Postmark-Server-Token'

    def __init__(self, api_key=None, secure=True, test=False,
                 **message):
        self.api_key = api_key
        if self.api_key is not None:
            self._headers[self._api_key_header_name] = self.api_key
        self.secure = secure
        self.test = test
        self.message = message

    def get_payload(self, message=None):
        if message is None:
            message = {}
        message.update(self.message)
        return json.dumps(message)

    def get_api_url(self, secure=None):
        if secure is None:
            secure = self.secure
        api_url = _POSTMARK_API
        if secure:
            api_url = _POSTMARK_API_SECURE
        return urljoin(api_url, self._endpoint)

    def send(self, api_key=None, test=False, secure=None,
             message=None, **kwargs):
        if api_key is None:
            api_key = self.api_key
            headers = self._headers
        else:
            # copy the base headers without overwriting the api key
            headers = {self._api_key_header_name: api_key}
            headers.update(self._headers)
        if api_key is None:
            raise ValueError('Postmark API Key not provided')
        if test is None:
            test = self.test
        url = self.get_api_url(secure=secure)
        data = self.get_payload(message=message)
        if test:
            return dict(url=url, data=data, headers=headers)
        return requests.post(url, data=data, headers=headers, **kwargs)


class PystBatchSender(PystSender):
    _endpoint = '/email/batch'

    def get_payload(self, message=None):
        if message is None:
            message = []
        [data.update(self.message_defaults) for data in message]
        return json.dumps(message)


class PystBounceHandler(object):
    pass
