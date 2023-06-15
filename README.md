# pystmark

[![PyPI version](https://badge.fury.io/py/pystmark.png)](http://badge.fury.io/py/pystmark)
[![Build Status](https://travis-ci.org/xsleonard/pystmark.png)](https://travis-ci.org/xsleonard/pystmark)
[![Coverage Status](https://coveralls.io/repos/xsleonard/pystmark/badge.png)](https://coveralls.io/r/xsleonard/pystmark)


[Postmark API](http://developer.postmarkapp.com/) library for python 2.7, 3.6 and pypy.
Built on top of the [requests](http://docs.python-requests.org/en/latest/) library.

## Web Framework Integration

* [Flask-Pystmark](https://github.com/xsleonard/flask-pystmark)

## Documentation

The full Sphinx-compiled documentation is available here: [https://readthedocs.org/docs/pystmark/en/latest/](https://readthedocs.org/docs/pystmark/en/latest/)

## Example Usage

```python
from pystmark import (
    Message,
    send,
    send_with_template,
    send_batch,
    send_batch_with_templates,
    UnauthorizedError
)

API_KEY = 'my_api_key'
SENDER = 'me@example.com'

# Send a single message
message = Message(
    sender=SENDER,
    to='you@example.com',
    subject='Hi',
    text='A message',
    tag='greeting'
)

response = send(message, api_key=API_KEY)

# Send a template message
model = {
    'user_name': 'John Smith',
    'company': {
      'name': 'ACME'
    }

message = Message(
    sender=SENDER,
    to='you@example.com',
    template_id=11111,
    template_model=model,
    tag='welcome',
)

response = send_with_template(message, api_key=API_KEY)

# Send multiple messages
messages = [
    Message(
        sender=SENDER,
        to='you@example.com',
        subject='Hi',
        text='A message',
        tag='greeting',
        message_stream='broadcasts',
    )
]

response = send_batch(messages, api_key=API_KEY)

# Send multiple messages with templates
messages = [
    Message(
        sender=SENDER,
        to='you@example.com',
        template_id=11111,
        template_model=model,
        tag='greeting',
        message_stream='broadcasts',
    )
]

response = send_batch_with_templates(messages, api_key=API_KEY)

# Check API response error
try:
    response.raise_for_status()
except UnauthorizedError:
    print 'Use your real API key'

# Check for errors in each message when sending batch emails:
for m in response.messages:
    if m.error_code > 0:
        print m.message
```

## Contribution

1. Fork this repo
2. Make your changes and write a test for them
3. Add yourself to the [AUTHORS.md](./AUTHORS.md) file and submit a pull request

Please run the tests with `./setup.py test --with-integration`, with at least python2.7,
before you make a pull request. Requirements for running the tests are in `tests/requirements.txt`.
The other versions will be handled by [travis-ci](https://travis-ci.org/).

The pep8 tests may fail if using pypy due to [this bug](https://bugs.pypy.org/issue1207),
so that test is disabled if pypy is detected.

## Copyright and License

pystmark is licensed under the MIT license. See the [LICENSE](./LICENSE) file for full details.
