import random
import string
import requests
from itertools import product
from urlparse import urljoin
from base64 import b64encode
from os import urandom
from mock import patch, Mock, MagicMock
from unittest import TestCase
from voluptuous import Schema, Optional, Invalid as InvalidSchema
import pystmark
from pystmark import (PystSender, PystBatchSender, PystMessage,
                      PystUnauthorizedError, PystUnprocessableEntityError,
                      PystInternalServerError, PystMessageError,
                      MAX_RECIPIENTS_PER_MESSAGE, MAX_BATCH_MESSAGES,
                      POSTMARK_API_TEST_KEY, POSTMARK_API_URL,
                      POSTMARK_API_URL_SECURE, PystInterface,
                      PystBounceError, PystBounces, PystBounce,
                      PystBounceActivate, PystBounceDump)

try:
    import simplejson as json
except ImportError:
    import json


def _make_random_string(n):
    return ''.join([random.choice(string.letters) for i in range(n)])


class RequestMock(object):

    def _raise(self, exc, *args, **kwargs):
        def f(*_args, **_kwargs):
            raise exc(*args, **kwargs)
        return f

    def mock_response(self, content, status_code=200, bad_json=False):
        mock = Mock(spec=requests.Response)
        mock.content = content
        mock.ok = (status_code >= 200 and status_code < 300)
        mock.status_code = status_code
        mock.iter_content = lambda size: mock.content
        if bad_json:
            mock.json = self._raise(ValueError)
        else:
            mock.json = lambda: json.loads(mock.content or '""')
        mock.raise_for_status = lambda: None
        return mock

    def _iterdata(self, data):
        data = list(data)

        def iterdata(*args, **kwargs):
            return self.mock_response(json.dumps(data.pop(0)))
        return iterdata

    def _setup_mock_request(self, mock_request, data):
        mock_request.side_effect = self._iterdata(data)


class PystTestCase(TestCase, RequestMock):

    response = None

    def assert200(self, r):
        self.assertEqual(r.status_code, 200)

    def assert500(self, r):
        self.assertEqual(r.status_code, 500)

    def assertNotRaises(self, exc, f, *args, **kwargs):
        try:
            f(*args, **kwargs)
        except exc as e:
            self.fail('Exception raised: {0} "{1}"'.format(type(e), e))

    def assertRaisesMessage(self, _exc, _msg, _f, *args, **kwargs):
        ''' Assserts that _exc was raised, and _msg is in str(_exc) '''
        msg_suffix = None
        try:
            _f(*args, **kwargs)
        except _exc as e:
            err = None
            try:
                err = str(e)
            except Exception as f:
                fmt = '{0} has no string representation'
                self.fail(fmt.format(f.__class__.__name__))
            finally:
                if err is None or _msg not in err:
                    self.fail('"{0}" not in "{1}".'.format(_msg, err))
            return
        try:
            msg = ', '.join([e.__name__ for e in _exc])
        except Exception:
            msg = _exc.__name__
        else:
            msg = '({0})'.format(msg)
        msg = '{0} not raised'.format(msg)
        if msg_suffix:
            msg = '{0} [{1}]'.format(msg, msg_suffix)
        self.fail(msg)

    def assertIs(self, a, b):
        # Python2.6 compatibility
        if hasattr(super(PystTestCase, self), 'assertIs'):
            super(PystTestCase, self).assertIs(a, b)
        else:
            self.assertTrue(a is b)

    def assertIsNot(self, a, b):
        # Python2.6 compatibility
        if hasattr(super(PystTestCase, self), 'assertIsNot'):
            super(PystTestCase, self).assertIsNot(a, b)
        else:
            self.assertTrue(a is not b)

    def assertValidJSONResponse(self, r, schema):
        self.assert200(r)
        self.assertValidJSONSchema(r.json(), schema)

    def assertValidJSONSchema(self, data, schema):
        self.assertIsNot(data, None)
        self.assertNotRaises(InvalidSchema, Schema(schema, required=True),
                             data)

    @property
    def json_response(self):
        return json.dumps(self.response)


class PystSenderTestBase(PystTestCase):

    response = {
        'ErrorCode': 0,
        'Message': 'OK',
        'MessageID': 'b7bc2f4a-e38e-4336-af7d-e6c392c2f817',
        'SubmittedAt': '2010-11-26T12:01:05.1794748-05:00',
        'To': 'receiver@example.com'
    }

    schema = {
        'ErrorCode': 0,
        'Message': unicode,
        'MessageID': unicode,
        'SubmittedAt': unicode,
        'To': unicode
    }

    message = {
        'From': 'sender@example.com',
        'To': 'receiver@example.com',
        'Cc': 'copied@example.com',
        'Bcc': 'blank-copied@example.com',
        'Subject': 'Test',
        'Tag': 'Invitation',
        'HtmlBody': '<b>Hello</b>',
        'TextBody': 'Hello',
        'ReplyTo': 'reply@example.com',
        'Headers': [{'Name': 'CUSTOM-HEADER', 'Value': 'value'}]
    }

    @property
    def sender(self):
        return PystSender(test=True)

    def send(self):
        return self.sender.send(message=self.message)


class PystSenderTest(PystSenderTestBase):

    @patch.object(requests.Session, 'request', autospec=True)
    def test_send_message(self, mock_request):
        mock_request.return_value = self.mock_response(self.json_response)
        r = self.send()
        self.assertValidJSONResponse(r, self.schema)

    @patch.object(requests.Session, 'request', autospec=True)
    def test_simple_api(self, mock_request):
        mock_request.return_value = self.mock_response(self.json_response)
        r = pystmark.send(self.message, test=True)
        self.assertValidJSONResponse(r, self.response)

    @patch('requests.request', autospec=True)
    def test_advanced_api(self, mock_request):
        mock_request.return_value = self.mock_response(self.json_response)
        message = pystmark.PystMessage(sender='me@example.com', text='hey')
        sender = pystmark.PystSender(message=message,
                                     api_key=POSTMARK_API_TEST_KEY)
        r = sender.send(dict(to='you@example.com'), test=True)
        self.assertValidJSONResponse(r, self.response)
        url = sender._get_api_url(secure=True)
        message.to = 'you@example.com'
        headers = sender._get_headers(api_key=POSTMARK_API_TEST_KEY)
        mock_request.assert_called_with('POST', url, data=message.json(),
                                        headers=headers)

    @patch('requests.request', autospec=True)
    def test_send_with_attachments(self, mock_request):
        mock_request.return_value = self.mock_response(self.json_response)
        message = pystmark.PystMessage(sender='me@example.com', text='hi',
                                       to='you@example.com')
        message.attach_binary(urandom(64), 'test.pdf')
        r = pystmark.send(message, api_key=POSTMARK_API_TEST_KEY)
        self.assertValidJSONResponse(r, self.response)


class PystResponseTest(PystSenderTestBase):

    @patch.object(requests.Session, 'request', autospec=True)
    def test_pyst_response_setter_wrap(self, mock_request):
        mock_request.return_value = self.mock_response('')
        r = self.send()
        r.dog = 'cat'
        self.assertEqual(r.dog, r._requests_response.dog)


class PystSenderArgsTest(PystSenderTestBase):

    @patch.object(requests.Session, 'request', autospec=True)
    def test_missing_api_key(self, mock_request):
        mock_request.return_value = self.mock_response('')
        sender = PystSender()
        msg = 'Postmark API Key not provided'
        self.assertRaisesMessage(ValueError, msg, sender.send)

    @patch('requests.request', autospec=True)
    def test_api_key_on_send(self, mock_request):
        mock_request.return_value = self.mock_response('')
        msg = PystMessage(to='me', text='hi')
        sender = PystSender(message=msg)
        url = sender._get_api_url(secure=True)
        data = msg.json()
        headers = sender._get_headers(api_key=POSTMARK_API_TEST_KEY)
        sender.send(api_key=POSTMARK_API_TEST_KEY)
        mock_request.assert_called_with('POST', url, data=data,
                                        headers=headers)

    def _test_secure_overrides(self, mock_request, init_secure=None,
                               send_secure=None):
        mock_request.return_value = self.mock_response('')
        msg = PystMessage(to='me', text='hi')
        sender = PystSender(test=True, secure=init_secure)
        if init_secure or init_secure is None:
            url = POSTMARK_API_URL_SECURE
        else:
            url = POSTMARK_API_URL
        if not send_secure and send_secure is not None:
            url = POSTMARK_API_URL
        elif send_secure:
            url = POSTMARK_API_URL_SECURE
        url = urljoin(url, PystSender.endpoint)
        data = msg.json()
        headers = sender._get_headers(api_key=POSTMARK_API_TEST_KEY)
        sender.send(secure=send_secure, message=msg)
        mock_request.assert_called_with('POST', url, data=data,
                                        headers=headers)

    @patch('requests.request', autospec=True)
    def test_secure_overrides(self, mock_request):
        xargs = product((True, False, None), repeat=2)
        for args in xargs:
            if args[0] is None:
                continue
            self._test_secure_overrides(mock_request, *args)

    def test_create_with_dict(self):
        sender = PystSender(message=self.message)
        self.assertEqual(sender.message, self.message)
        self.assertNotEqual(sender.message, PystMessage(to='me', text='hi'))


class PystSenderErrorTest(PystSenderTestBase):

    @patch.object(requests.Session, 'request', autospec=True)
    def test_401(self, mock_request):
        mock_request.return_value = self.mock_response('{}', status_code=401)
        r = self.send()
        self.assertRaises(PystUnauthorizedError, r.raise_for_status)

    @patch.object(requests.Session, 'request', autospec=True)
    def test_422(self, mock_request):
        mock_request.return_value = self.mock_response('{}', status_code=422)
        r = self.send()
        self.assertRaises(PystUnprocessableEntityError, r.raise_for_status)

    @patch.object(requests.Session, 'request', autospec=True)
    def test_500(self, mock_request):
        mock_request.return_value = self.mock_response('{}', status_code=500)
        r = self.send()
        self.assertRaises(PystInternalServerError, r.raise_for_status)

    @patch.object(requests.Session, 'request', autospec=True)
    def test_unhandled_status(self, mock_request):
        mock_request.return_value = self.mock_response('{}', status_code=418)
        r = self.send()
        self.assertNotRaises(Exception, r.raise_for_status)
        self.assertIs(r.raise_for_status(), None)


class PystMessageTest(PystSenderTestBase):

    def test_load_message_native(self):
        msg = dict(to='me', text='hi', html='<b>hi</b>', reply_to='you',
                   cc='dog,cat', subject='dogs', headers=[dict(Name='Food',
                                                               Value='7')])
        self.assertNotRaises(TypeError, PystMessage.load_message, msg)
        self.assertNotRaises(PystMessageError, PystMessage.load_message, msg,
                             verify=True)
        msg = dict(to='me', text='hi')
        self.assertNotRaises(TypeError, PystMessage.load_message, msg)
        self.assertNotRaises(PystMessageError, PystMessage.load_message, msg,
                             verify=True)
        pystmsg = PystMessage.load_message(msg)
        self.assertEqual(pystmsg.data(), dict(To='me', TextBody='hi'))

    def test_load_message_postmark(self):
        self.assertNotRaises(TypeError, PystMessage.load_message,
                             self.message)
        msg = PystMessage.load_message(self.message)
        self.assertNotRaises(PystMessageError, PystMessage.load_message,
                             self.message, verify=True)
        self.assertEqual(msg.data(), self.message)

    def test_load_invalid_message_no_data(self):
        msg = PystMessage.load_message(dict())
        self.assertRaises(PystMessageError, msg.verify)

    def test_load_invalid_message_some_data(self):
        msg = PystMessage.load_message(dict(to='me'))
        self.assertRaises(PystMessageError, msg.verify)

    def test_load_invalid_message_unrecognized_field(self):
        self.assertRaises(TypeError, PystMessage.load_message, dict(dog='me'))

    def test_equal(self):
        m = PystMessage(sender='me')
        n = PystMessage(sender='me')
        self.assertEqual(m, n)

    def test_not_equal(self):
        m = PystMessage(sender='me')
        n = PystMessage(sender='you')
        self.assertNotEqual(m, n)


class PystMessageErrorTest(PystSenderTestBase):

    def test_missing_to(self):
        self.assertRaisesMessage(PystMessageError, '"to" is required',
                                 PystMessage, verify=True)

    def test_sender_verification(self):
        self.assertRaises(PystMessageError, self.sender.send)

    def test_missing_html_and_text(self):
        err = 'At least one of "html" or "text" must be provided'
        self.assertRaisesMessage(PystMessageError, err, PystMessage, to='me',
                                 verify=True)

    def _test_bad_headers(self, errmsg, bad_header):
        self.assertRaisesMessage(PystMessageError, errmsg, PystMessage,
                                 to='me', text='hi', headers=[bad_header],
                                 verify=True)

    def test_bad_headers_extra_fields(self):
        err = 'Header must contain only "Name" and "Value"'
        bad_header = dict(Name='dog', Value='dog', bad='dog')
        self._test_bad_headers(err, bad_header)

    def test_bad_headers_missing_name(self):
        err = 'Header must contain "Name"'
        bad_header = dict(Value='dog')
        self._test_bad_headers(err, bad_header)

    def test_bad_headers_missing_value(self):
        err = 'Header must contain "Value"'
        bad_header = dict(Name='dog')
        self._test_bad_headers(err, bad_header)

    def test_bad_headers_not_dict(self):
        err = 'Invalid Header value'
        bad_header = 'bad'
        self._test_bad_headers(err, bad_header)

    def test_attach_header(self):
        msg = PystMessage(to='me', text='hi')
        msg.add_header('Boy', 'Dog')
        self.assertEqual(msg.headers, [dict(Name='Boy', Value='Dog')])

    def _test_bad_attachments(self, errmsg, bad_attachment):
        self.assertRaisesMessage(PystMessageError, errmsg, PystMessage,
                                 to='me', text='hi',
                                 attachments=[bad_attachment], verify=True)

    def test_bad_attachment_extra_field(self):
        err = 'Attachment must contain only'
        bad = dict(Name='text.txt', ContentType='application/octet-stream',
                   Content='csacasd', bad='dog')
        self._test_bad_attachments(err, bad)

    def test_bad_attachment_missing_name(self):
        err = 'Attachment must contain "Name"'
        bad = dict(ContentType='application/octet-stream', Content='csacasd')
        self._test_bad_attachments(err, bad)

    def test_bad_attachment_missing_content_type(self):
        err = 'Attachment must contain "ContentType"'
        bad = dict(Name='text.txt', Content='csacasd')
        self._test_bad_attachments(err, bad)

    def test_bad_attachment_missing_content(self):
        err = 'Attachment must contain "Content"'
        bad = dict(Name='text.txt', ContentType='application/octet-stream')
        self._test_bad_attachments(err, bad)

    def test_attach_bad_filename(self):
        err = 'Filename not found in path'
        msg = PystMessage(to='me', text='hi')
        self.assertRaisesMessage(PystMessageError, err, msg.attach_file,
                                 '/bad/path/')

    def test_attach_nonexistant_filename(self):
        msg = PystMessage(to='me', text='hi')
        self.assertRaisesMessage(IOError, 'No such file', msg.attach_file,
                                 'bad.pdf')

    def test_attach_file_no_extension(self):
        msg = PystMessage(to='me', text='hi')
        err = 'requires an extension'
        with patch('__builtin__.open', create=True) as mock_open:
            mock_file = MagicMock(spec=file)
            mock_file.read = lambda: 'x'
            mock_open.return_value = mock_file
            self.assertRaisesMessage(PystMessageError, err, msg.attach_file,
                                     'bad')

    def test_attach_file_banned_extension(self):
        msg = PystMessage(to='me', text='hi')
        err = 'is not allowed'
        with patch('__builtin__.open', create=True) as mock_open:
            mock_file = MagicMock(spec=file)
            mock_file.read = lambda: 'x'
            mock_open.return_value = mock_file
            self.assertRaisesMessage(PystMessageError, err, msg.attach_file,
                                     'bad.exe')

    def test_attach_binary(self):
        msg = PystMessage(to='me', text='hi')
        data = urandom(64)
        name = 'test.pdf'
        msg.attach_binary(data, name)
        attachment = {
            'Content': b64encode(data),
            'ContentType': 'application/pdf',
            'Name': name
        }
        self.assertEqual(msg.attachments, [attachment])

    def test_attach_binary_default_content_type(self):
        msg = PystMessage(to='me', text='hi')
        data = urandom(64)
        name = 'test.mobi'
        msg.attach_binary(data, name)
        attachment = {
            'Content': b64encode(data),
            'ContentType': 'application/octet-stream',
            'Name': name
        }
        self.assertEqual(msg.attachments, [attachment])

    def test_attach_binary_content_type_override(self):
        msg = PystMessage(to='me', text='hi')
        data = urandom(64)
        content_type = 'xcascasc'
        name = 'test.pdf'
        msg.attach_binary(data, name, content_type=content_type)
        attachment = {
            'Content': b64encode(data),
            'ContentType': content_type,
            'Name': name
        }
        self.assertEqual(msg.attachments, [attachment])

    def test_too_many_recipients(self):
        err = 'No more than {0} recipients accepted'
        MAX = MAX_RECIPIENTS_PER_MESSAGE
        err = err.format(MAX)
        recipients = ['hi@me.com' for i in range(MAX + 1)]
        # to
        self.assertRaisesMessage(PystMessageError, err, PystMessage,
                                 to=recipients, text='hi', verify=True)
        # cc
        recipients = ['hi@me.com' for i in range(MAX + 1)]
        self.assertRaisesMessage(PystMessageError, err, PystMessage,
                                 to='hi@me.com', text='hi', cc=recipients,
                                 verify=True)
        # bcc
        recipients = ['hi@me.com' for i in range(MAX + 1)]
        self.assertRaisesMessage(PystMessageError, err, PystMessage,
                                 to='hi@me.com', text='hi', cc=recipients,
                                 verify=True)
        # at limit, but not over
        recipients.pop()
        self.assertNotRaises(PystMessageError, PystMessage, to=recipients,
                             text='hi', verify=True)

    def test_recipient_setters(self):
        message = PystMessage(to='hi,me', cc='you,other', bcc='dog,cat,cow')
        self.assertEqual(len(message.recipients), 7)

    def test_verify_on_init(self):
        self.assertRaises(PystMessageError, PystMessage, verify=True)
        self.assertNotRaises(PystMessageError, PystMessage, to='me', text='hi',
                             verify=True)


class PystErrorTest(PystSenderTestBase):

    @patch.object(requests.Session, 'request')
    def test_bad_json_response(self, mock_request):
        mock_request.return_value = self.mock_response('{"}', status_code=500)
        r = self.send()
        msg = 'Not a valid JSON response'
        self.assertRaisesMessage(PystInternalServerError, msg,
                                 r.raise_for_status)

    @patch.object(requests.Session, 'request')
    def test_error_str_formatted_postmark(self, mock_request):
        err = dict(ErrorCode=10, Message='Internal Server Error')
        mock_request.return_value = self.mock_response(json.dumps(err),
                                                       status_code=500)
        r = self.send()
        msg = '{1} [ErrorCode {0}]'.format(err['ErrorCode'], err['Message'])
        self.assertRaisesMessage(PystInternalServerError, msg,
                                 r.raise_for_status)


class PystBatchSenderTestBase(PystSenderTestBase):

    response = [PystSenderTestBase.response] * 10

    schema = [PystSenderTestBase.schema]

    _message_count = 20

    def setUp(self):
        super(PystBatchSenderTestBase, self).setUp()
        self._messages = None

    @property
    def message_count(self):
        return self._message_count

    @message_count.setter
    def message_count(self, v):
        if v != self._message_count:
            self._messages = None
        self._message_count = v

    @property
    def messages(self):
        if self._messages is not None:
            return self._messages
        msgs = [{}] * self.message_count
        [msg.update(self.message) for msg in msgs]
        for msg in msgs:
            msg['To'] = '{0}@example.com'.format(_make_random_string(10))
        return msgs

    @property
    def sender(self):
        return PystBatchSender(api_key=POSTMARK_API_TEST_KEY, test=True)

    def send(self):
        return self.sender.send(messages=self.messages)


class PystBatchSenderTest(PystBatchSenderTestBase):

    @patch.object(requests.Session, 'request')
    def test_batch_send(self, mock_request):
        mock_request.return_value = self.mock_response(self.json_response)
        r = self.send()
        self.assertValidJSONResponse(r, self.schema)

    @patch.object(requests.Session, 'request')
    def test_batch_send_no_messages(self, mock_request):
        mock_request.return_value = self.mock_response(self.json_response)
        msg = 'No messages to send'
        self.assertRaisesMessage(PystMessageError, msg, self.sender.send,
                                 messages=None)
        self.assertRaisesMessage(PystMessageError, msg, self.sender.send,
                                 messages=[])

    @patch.object(requests.Session, 'request')
    def test_batch_send_too_many_messages(self, mock_request):
        mock_request.return_value = self.mock_response(self.json_response)
        self.message_count = MAX_BATCH_MESSAGES + 1
        msg = 'Maximum {0} messages allowed in batch'
        msg = msg.format(MAX_BATCH_MESSAGES)
        self.assertRaisesMessage(PystMessageError, msg, self.sender.send,
                                 messages=self.messages)

    @patch.object(requests.Session, 'request')
    def test_simple_api(self, mock_request):
        mock_request.return_value = self.mock_response(self.json_response)
        r = pystmark.send_batch(self.messages, test=True)
        self.assertValidJSONResponse(r, self.schema)


class PystBouncesTest(PystTestCase):

    response = {
        'TotalCount': 30,
        'Bounces': [
            {
                'ID': 777,
                'Type': 'Transient',
                'TypeCode': 2,
                'Name': 'Message delayed',
                'Tag': 'email_confirmation',
                'MessageID': 'xxx',
                'Description': ('The server could not temporarily deliver '
                                'your message (ex:  Message is delayed due to '
                                'network troubles).'),
                'Details': 'action:  failed\r\n',
                'Email': 'test@gamail.com',
                'BouncedAt': '2013-05-02T12: 05: 30.3885278-04: 00',
                'DumpAvailable': True,
                'Inactive': False,
                'CanActivate': True,
                'Subject': 'Confirm your account'
            }
        ]
    }

    schema = {
        'TotalCount': int,
        'Bounces': [
            {
                'ID': int,
                'Type': unicode,
                'TypeCode': int,
                'Name': unicode,
                'Tag': unicode,
                'MessageID': unicode,
                'Description': unicode,
                'Details': unicode,
                'Email': unicode,
                'BouncedAt': unicode,
                'DumpAvailable': bool,
                'Inactive': bool,
                'CanActivate': bool,
                'Subject': unicode
            }
        ]
    }

    @patch.object(requests.Session, 'request')
    def test_simple_api(self, mock_request):
        mock_request.return_value = self.mock_response(self.json_response)
        r = pystmark.get_bounces(test=True)
        self.assertValidJSONResponse(r, self.schema)

    @patch.object(requests.Session, 'request')
    def test_bad_json_response(self, mock_request):
        mock_request.return_value = self.mock_response(self.json_response,
                                                       bad_json=True)
        r = pystmark.get_bounces(test=True)
        self.assertEqual(r.bounces, [])
        self.assertEqual(r.total, 0)

    @patch.object(requests.Session, 'request')
    def test_bad_bounce_type(self, mock_request):
        mock_request.return_value = self.mock_response(self.json_response)
        b = PystBounces()
        self.assertRaisesMessage(PystBounceError, 'Invalid bounce type',
                                 b.get, 'xxx', test=True)

    @patch.object(requests.Session, 'request')
    def test_bounce_type(self, mock_request):
        mock_request.return_value = self.mock_response(self.json_response)
        b = PystBounces()
        b.get(bounce_type='HardBounce', test=True)
        params = dict(type='HardBounce', count=25, offset=0)
        headers = b._get_headers(test=True)
        url = b._get_api_url(test=True)
        mock_request.assert_called_with(method='GET', url=url, headers=headers,
                                        params=params)

    @patch.object(requests.Session, 'request')
    def test_inactive_true(self, mock_request):
        mock_request.return_value = self.mock_response(self.json_response)
        b = PystBounces()
        b.get(bounce_type='HardBounce', inactive=True, test=True)
        params = dict(type='HardBounce', inactive=True, count=25, offset=0)
        headers = b._get_headers(test=True)
        url = b._get_api_url(test=True)
        mock_request.assert_called_with(method='GET', url=url, headers=headers,
                                        params=params)

    @patch.object(requests.Session, 'request')
    def test_inactive_false(self, mock_request):
        mock_request.return_value = self.mock_response(self.json_response)
        b = PystBounces()
        b.get(bounce_type='HardBounce', inactive=False, test=True)
        params = dict(type='HardBounce', inactive=False, count=25, offset=0)
        headers = b._get_headers(test=True)
        url = b._get_api_url(test=True)
        mock_request.assert_called_with(method='GET', url=url, headers=headers,
                                        params=params)

    @patch.object(requests.Session, 'request')
    def test_email_filter(self, mock_request):
        mock_request.return_value = self.mock_response(self.json_response)
        b = PystBounces()
        b.get(bounce_type='HardBounce', email_filter='@gmail.com', test=True)
        params = dict(type='HardBounce', emailFilter='@gmail.com', count=25,
                      offset=0)
        headers = b._get_headers(test=True)
        url = b._get_api_url(test=True)
        mock_request.assert_called_with(method='GET', url=url, headers=headers,
                                        params=params)

    @patch.object(requests.Session, 'request')
    def test_message_id(self, mock_request):
        mock_request.return_value = self.mock_response(self.json_response)
        b = PystBounces()
        b.get(bounce_type='HardBounce', message_id='xxx-yyy', test=True)
        params = dict(type='HardBounce', messageID='xxx-yyy')
        headers = b._get_headers(test=True)
        url = b._get_api_url(test=True)
        mock_request.assert_called_with(method='GET', url=url, headers=headers,
                                        params=params)

    @patch.object(requests.Session, 'request')
    def test_message_id_with_count(self, mock_request):
        mock_request.return_value = self.mock_response(self.json_response)
        b = PystBounces()
        b.get(bounce_type='HardBounce', message_id='xxx-yyy', count=7,
              offset=2, test=True)
        params = dict(type='HardBounce', messageID='xxx-yyy', count=7,
                      offset=2)
        headers = b._get_headers(test=True)
        url = b._get_api_url(test=True)
        mock_request.assert_called_with(method='GET', url=url, headers=headers,
                                        params=params)


class PystBounceTest(PystTestCase):

    bounce_id = 777
    response = PystBouncesTest.response['Bounces'][0]
    schema = PystBouncesTest.schema['Bounces'][0]

    @patch.object(requests.Session, 'request')
    def test_simple_api(self, mock_request):
        mock_request.return_value = self.mock_response(self.json_response)
        r = pystmark.get_bounce(self.bounce_id, test=True)
        self.assertValidJSONResponse(r, self.schema)

    @patch.object(requests.Session, 'request')
    def test_bad_json_response(self, mock_request):
        mock_request.return_value = self.mock_response(self.json_response,
                                                       bad_json=True)
        r = pystmark.get_bounce(self.bounce_id, test=True)
        self.assertIs(r.bounce, None)


class PystBounceDumpTest(PystTestCase):

    bounce_id = 777
    response = {
        'Body': 'blah'
    }

    @patch.object(requests.Session, 'request')
    def test_simple_api(self, mock_request):
        mock_request.return_value = self.mock_response(self.json_response)
        r = pystmark.get_bounce_dump(self.bounce_id, test=True)
        self.assertValidJSONResponse(r, self.response)

    @patch.object(requests.Session, 'request')
    def test_dump_of_fetched_message(self, mock_request):
        # Fetch a bounce
        _response = self.response
        self.response = PystBounceTest.response
        mock_request.return_value = self.mock_response(self.json_response)
        r = pystmark.get_bounce(self.bounce_id, test=True)
        self.assertValidJSONResponse(r, PystBounceTest.schema)

        # Fetch the dump via the bounce object
        old_r = r
        self.response = _response
        mock_request.return_value = self.mock_response(self.json_response)
        r = old_r.bounce.dump(test=True)
        self.assertValidJSONResponse(r, self.response)

        # Fetch the dump via the bounce object, using the default sender
        self.response = _response
        mock_request.return_value = self.mock_response(self.json_response)
        old_r.bounce._sender = None
        r = old_r.bounce.dump(test=True)
        self.assertValidJSONResponse(r, self.response)

    @patch.object(requests.Session, 'request')
    def test_bad_json_response(self, mock_request):
        mock_request.return_value = self.mock_response(self.json_response,
                                                       bad_json=True)
        r = pystmark.get_bounce_dump(self.bounce_id, test=True)
        self.assertIs(r.dump, None)


class PystBounceTagsTest(PystTestCase):

    response = ['Signup', 'Notification']

    @patch.object(requests.Session, 'request')
    def test_simple_api(self, mock_request):
        mock_request.return_value = self.mock_response(self.json_response)
        r = pystmark.get_bounce_tags(test=True)
        self.assertValidJSONResponse(r, self.response)

    @patch.object(requests.Session, 'request')
    def test_bad_json_response(self, mock_request):
        mock_request.return_value = self.mock_response(self.json_response,
                                                       bad_json=True)
        r = pystmark.get_bounce_tags(test=True)
        self.assertEqual(r.tags, [])


class PystBounceActivateTest(PystTestCase):

    bounce_id = 777
    response = {
        'Message': 'OK',
        'Bounce': PystBouncesTest.response['Bounces'][0]
    }

    schema = {
        'Message': unicode,
        'Bounce': PystBouncesTest.schema['Bounces'][0]
    }

    @patch.object(requests.Session, 'request')
    def test_simple_api(self, mock_request):
        mock_request.return_value = self.mock_response(self.json_response)
        r = pystmark.activate_bounce(self.bounce_id, test=True)
        self.assertValidJSONResponse(r, self.schema)

    @patch.object(requests.Session, 'request')
    def test_bad_json_response(self, mock_request):
        mock_request.return_value = self.mock_response(self.json_response,
                                                       bad_json=True)
        r = pystmark.activate_bounce(self.bounce_id, test=True)
        self.assertIs(r.bounce, None)


class PystDeliveryStatsTest(PystTestCase):

    response = {
        'InactiveMails': 26,
        'Bounces': [
            {
                'Name': 'All',
                'Count': 30
            },
            {
                'Type': 'HardBounce',
                'Name': 'Hard bounce',
                'Count': 26
            },
            {
                'Type': 'Transient',
                'Name': 'Message delayed',
                'Count': 3
            },
            {
                'Type': 'Blocked',
                'Name': 'ISP block',
                'Count': 1
            }
        ]
    }

    schema = {
        'InactiveMails': int,
        'Bounces': [
            {
                'Name': unicode,
                'Count': int,
                Optional('Type'): unicode,
            }
        ]
    }

    @patch.object(requests.Session, 'request')
    def test_simple_api(self, mock_request):
        mock_request.return_value = self.mock_response(self.json_response)
        r = pystmark.get_delivery_stats(test=True)
        self.assertValidJSONResponse(r, self.schema)
        self.assertEqual(r.total, 30)
        self.assertEqual(r.inactive, 26)
        self.assertEqual(len(r.bounces), 4)
        self.assertEqual(r.bounces['Blocked'].name, 'ISP block')

    @patch.object(requests.Session, 'request')
    def test_bad_json_response(self, mock_request):
        mock_request.return_value = self.mock_response(self.json_response,
                                                       bad_json=True)
        r = pystmark.get_delivery_stats(test=True)
        self.assertEqual(r.total, 0)
        self.assertEqual(r.inactive, 0)
        self.assertEqual(r.bounces, {})


class UserWarningsTest(PystTestCase):

    def test_missing_attributes(self):

        class Dummy(PystInterface):
            pass

        self.assertRaises(NotImplementedError, Dummy()._get_api_url)
        self.assertRaises(NotImplementedError, Dummy()._request, 'dog')
