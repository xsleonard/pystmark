# -*- coding: ascii -*-

"""
    pystmark
    --------

    Postmark API library built on :mod:`requests`

    :copyright: 2013, see AUTHORS for more details
    :license: MIT, see LICENSE for more details

    :TODO:
        Attachments
        Bounce handler
        Tests
        Prevalidation of messages
        Use the PystResponse
"""

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

_POSTMARK_API = 'http://api.postmarkapp.com/'
_POSTMARK_API_SECURE = 'https://api.postmarkapp.com/'
_POSTMARK_API_TEST_KEY = 'POSTMARK_API_TEST'


class PystError(Exception):
    """Base `Exception` for :mod:`pystmark` errors."""
    message = ''

    def __init__(self, request, response):
        self.request = request
        self.response = response

    def __str__(self):
        return str(self.message)


class PystUnauthorizedError(Exception):
    """Thrown when Postmark responds with a :attr:`status_code` of 401
    Indicates a missing or incorrect API key.
    """
    message = "Missing or incorrect API Key header."


class PystUnprocessableEntityError(Exception):
    """Thrown when Postmark responds with a :attr:`status_code` of 422.
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
    """Thrown when Postmark responds with a :attr:`status_code` of 500
    Indicates an error on Postmark's end. Any messages sent
    in the request were not received by them.
    """
    message = "Postmark Internal Server Error. {0} message{1} lost"

    def __str__(self):
        ct = len(self.request.messages)
        s = 's' if ct > 1 else ''
        return self.message.format(ct, s)


class PystResponse(requests.Response):
    """Wrapper around :class:`requests.Response`."""

    def raise_on_status(self):
        """Raise Postmark-specific error messages"""
        if self.status_code == 401:
            raise PystUnauthorizedError(self.request, self)
        elif self.status_code == 422:
            raise PystUnprocessableEntityError(self.request, self)
        elif self.status_code == 500:
            raise PystInternalServerError(self.request, self)
        return super(PystResponse, self).raise_on_status()


class PystSender(object):
    """A wrapper for the Postmark API.

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
    """

    _endpoint = '/email'
    _headers = {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
    }
    _api_key_header_name = 'X-Postmark-Server-Token'

    def __init__(self, message=None, api_key=None, secure=True,
                 test=False, request_args=None):
        if message is None:
            message = {}
        self.message = message
        self.api_key = api_key
        if self.api_key is not None:
            self._headers[self._api_key_header_name] = self.api_key
        self.secure = secure
        self.test = test
        if request_args is None:
            request_args = {}
        self.request_args = request_args

    def _reverse_update(self, src, dest):
        """Updates dest with values from src if key in src is not
        present in dest

        :param src: Data to use as defaults for dest.
        :type src: :keyword:`dict`.
        :param dest: Object to load defaults to.
        :type dest: :keyword:`dict`.
        :type message: :keyword:`dict`
        """
        for k, v in src.iteritems():
            dest.setdefault(k, v)

    def _merge_request_args(self, request_args):
        """Merges request_args to be passed to :func:`requests.request`
        Since request_args possibly contains :keyword:`dict`s itself,
        we need to :meth:`_reverse_update` these.

        :param request_args: request_args mapping to be updated
        :type request_args: :keyword:`dict`
        """
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

    def _get_payload(self, message=None):
        """Updates message with default message paramaters.

        :param message: Postmark message data
        :type message: :keyword:`dict`
        :rtype: JSON encoded :keyword:`unicode`
        """
        if message is None:
            message = {}
        self._reverse_update(self.message, message)
        return json.dumps(message, ensure_ascii=False)

    def _get_api_url(self, secure=None):
        """Constructs Postmark API url

        :param secure': Use the https Postmark API.
        :rtype: Postmark API url
        """
        if secure is None:
            secure = self.secure
        api_url = _POSTMARK_API
        if secure:
            api_url = _POSTMARK_API_SECURE
        return urljoin(api_url, self._endpoint)

    def send(self, message=None, api_key=None, test=None,
             secure=None, request_args=None):
        """Send request to Postmark API.
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
        """
        headers = {}
        if test is None:
            test = self.test
        if api_key is None:
            api_key = self.api_key
            headers.update(self._headers)
        else:
            headers[self._api_key_header_name] = api_key
        if api_key is None and not test:
            raise ValueError('Postmark API Key not provided')
        if request_args is None:
            request_args = {}
        self._merge_request_args(request_args)
        if test:
            headers[self._api_key_header_name] = _POSTMARK_API_TEST_KEY
        self._reverse_update(request_args.setdefault('headers', {}),
                             headers)
        del request_args['headers']
        data = self.get_payload(message)
        self._reverse_update(request_args.setdefault('data', {}),
                             data)
        del request_args['data']
        url = self.get_api_url(secure=secure)
        return requests.post(url, data=data, headers=headers,
                             **request_args)


class PystBatchSender(PystSender):
    """A wrapper for the Postmark Batch API.

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
    """

    _endpoint = '/email/batch'

    def _get_payload(self, message=None):
        """Updates all messages in message with default message
        parameters.

        :param message: A collection of Postmark message data
        :type message: a collection of message :keyword:`dict`s
        :rtype: JSON encoded :keyword:`unicode`
        """
        if message is None:
            message = []
        [self._reverse_update(self.message, msg) for msg in message]
        return json.dumps(message, ensure_ascii=False)

    def send(self, message=None, api_key=None, test=None,
             secure=None, request_args=None):
        """Send batch request to Postmark API.
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
        """
        return super(PystBatchSender, self).send(
            message=message, api_key=api_key, test=test, secure=secure,
            request_args=request_args)


class PystBounceHandler(object):
    pass
