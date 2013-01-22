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
    """Wrapper around :class:`requests.Response`. Overrides
    :meth:`requests.Response.raise_on_status` to give Postmark-specific
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
    """A wrapper for the Postmark API.

    All of the arguments used in constructing this object are
    used as defaults in the actual :meth:`Pystmark.send` call.
    You can override any of them at that time. Typically, the only
    unique data that you would have to use in a call to
    :meth:`Pystmark.send` is Postmark API data unique to the message
    you are sending.

    :param message: A :keyword:`dict` containing defaults to populate
    any outgoing Postmark API requests. Default to {}.
    :param api_key: Your Postmark API key. Defaults to None. If not
    provided, you must provided it in your call to
    :meth:`PystSender.send`
    :param secure: If True, uses the https scheme for Postmark API
    requests. Defaults to True.
    :param test: If True, no request will be made to the API url, and
    :meth:`PystSender.send` will return a dict containing data that
    would have been sent.
    :param \*\*request_args: Any default arguments to pass to
    :func:`requests.post` when making the request to the Postmark API.
    """

    _endpoint = '/email'
    _headers = {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
    }
    _api_key_header_name = 'X-Postmark-Server-Token'

    def __init__(self, message=None, api_key=None, secure=True,
                 test=False, **request_args):
        if message is None:
            message = {}
        self.message = message
        self.api_key = api_key
        if self.api_key is not None:
            self._headers[self._api_key_header_name] = self.api_key
        self.secure = secure
        self.test = test
        self.request_args = request_args

    def _update_message(self, message):
        """Loads defaults from :attr:`self.message` onto a message

        :param message: A `dict` containing Postmark request data.
        """
        for k, v in self.message:
            message.setdefault(k, v)

    def _get_payload(self, message=None):
        """Updates message with default message paramaters.
        Returns a json encoded string

        :param message: A :keyword:`dict` to be sent to Postmark
        as json. Defaults to `self.message`.
        """
        if message is None:
            message = {}
        self._update_message(message)
        return json.dumps(message)

    def _get_api_url(self, secure=None):
        """Returns url to send a Postmark request to

        :param secure': Use the https Postmark API. Overrides value
        given to :meth:`PystSender.__init__`. Defaults to `self.secure`.
        """
        if secure is None:
            secure = self.secure
        api_url = _POSTMARK_API
        if secure:
            api_url = _POSTMARK_API_SECURE
        return urljoin(api_url, self._endpoint)

    def send(self, message=None, api_key=None, test=None, secure=None,
             **request_args):
        """Send request to Postmark API.
        Returns result of :func:`requests.post` if not testing.
        Returns :keyword:`dict` containing 'url', 'data', 'headers' and
        'request_args' if testing.

        :param message: A :keyword:`dict` containing your Postmark
        message data. Defaults to `self.message`.
        :param api_key: Your Postmark API key. Defaults to
        `self.api_key`
        :param test: Don't send message to Postmark, but return the
        payload that would have been sent. Returns a :keyword:`dict`
        containing 'url', 'data', 'headers' and 'request_args'.
        Defaults to `self.test`.
        :param secure': Use the https Postmark API. Defaults to
        `self.secure`
        :param \*\*request_args: Extra arguments to pass to
        :func:`requests.post`
        """
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
        data = self.get_payload(message)
        request_args.update(self.request_args)
        if test:
            return dict(url=url, data=data, headers=headers,
                        request_args=request_args)
        return requests.post(url, data=data, headers=headers,
                             **request_args)


class PystBatchSender(PystSender):
    """A wrapper for the Postmark Batch API.

    Its the same as :class:`PystSender`, except the message
    keyword argument in :meth:`PystSender.__init__` and
    :meth:`PystSender.send` must be an array of message
    :keyword:`dict`s, if provided.
    """

    _endpoint = '/email/batch'

    def _get_payload(self, message=None):
        """Updates all messages in message with default message
        parameters. Returns a json encoded string.

        :param message: An array of dicts containing Postmark request
        data. Defaults to [].
        """
        if message is None:
            message = []
        [self._update_message(msg) for msg in message]
        return json.dumps(message)


class PystBounceHandler(object):
    pass
