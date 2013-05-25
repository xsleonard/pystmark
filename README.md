# pystmark

[Postmark API](http://developer.postmarkapp.com/) library for python 2.6 and 2.7.
Built on top of the [requests](http://docs.python-requests.org/en/latest/) library.

[![Build Status](https://travis-ci.org/xsleonard/pystmark.png)](https://travis-ci.org/xsleonard/pystmark)


## Documentation

The full Sphinx-compiled documentation is available here: [https://readthedocs.org/docs/pystmark/en/latest/](https://readthedocs.org/docs/pystmark/en/latest/)

## Example Usage

```python
import pystmark

API_KEY = 'my_api_key'
SENDER = 'me@example.com'

# Send a single message
message = pystmark.PystMessage(sender=SENDER, to='you@example.com',
                               subject='Hi', text='A message', tag='greeting')
pystmark.send(message, api_key=API_KEY)


# Send multiple messages (via Postmark's batch send API)
recipients = ['you{0}@example.com'.format(i) for i in xrange(20)]
messages = [pystmark.PystMessage(sender=SENDER, to=to, subject='Hi',
                                 text='A message', tag='greeting')
            for to in recipients]

response = pystmark.send_batch(messages, api_key=API_KEY)

# Check API response error
try:
    response.raise_for_status()
except pystmark.PystUnauthorizedError:
    print 'Use your real API key'

```


## Contribution

1. Fork this repo
2. Make your changes and write a test for them
3. Add yourself to the AUTHORS file and submit a pull request

Please run the tests with `./setup.py test` before you make a pull request.
Requirements for running the tests are in `tests/requirements.pip`.


## Copyright and License

pystmark is licensed under the MIT license. See the LICENSE file for full details.
