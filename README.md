# pystmark

[![PyPI version](https://badge.fury.io/py/pystmark.png)](http://badge.fury.io/py/pystmark)
[![Build Status](https://travis-ci.org/xsleonard/pystmark.png)](https://travis-ci.org/xsleonard/pystmark)
[![Coverage Status](https://coveralls.io/repos/xsleonard/pystmark/badge.png)](https://coveralls.io/r/xsleonard/pystmark)


[Postmark API](http://developer.postmarkapp.com/) library for python 2.6, 2.7, 3.3 and pypy.
Built on top of the [requests](http://docs.python-requests.org/en/latest/) library.

## Web Framework Integration

* [Flask-Pystmark](https://github.com/xsleonard/flask-pystmark)

## Documentation

The full Sphinx-compiled documentation is available here: [https://readthedocs.org/docs/pystmark/en/latest/](https://readthedocs.org/docs/pystmark/en/latest/)

## Example Usage

```python
import pystmark

API_KEY = 'my_api_key'
SENDER = 'me@example.com'

# Send a single message
message = pystmark.Message(sender=SENDER, to='you@example.com', subject='Hi',
                           text='A message', tag='greeting')
pystmark.send(message, api_key=API_KEY)


# Send multiple messages (via Postmark's batch send API)
recipients = ['you{0}@example.com'.format(i) for i in xrange(20)]
messages = [pystmark.Message(sender=SENDER, to=to, subject='Hi',
                             text='A message', tag='greeting')
            for to in recipients]

response = pystmark.send_batch(messages, api_key=API_KEY)

# Check API response error
try:
    response.raise_for_status()
except pystmark.UnauthorizedError:
    print 'Use your real API key'

```

## Contribution

1. Fork this repo
2. Make your changes and write a test for them
3. Add yourself to the AUTHORS file and submit a pull request

Please run the tests with `./setup.py test --with-integration`, with at least python2.7,
before you make a pull request. Requirements for running the tests are in `tests/requirements.txt`.
The other versions will be handled by [travis-ci](https://travis-ci.org/).

The pep8 tests may fail if using pypy due to [this bug](https://bugs.pypy.org/issue1207),
so that test is disabled if pypy is detected.

## Copyright and License

pystmark is licensed under the MIT license. See the LICENSE file for full details.
