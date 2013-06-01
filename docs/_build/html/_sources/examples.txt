.. module:: pystmark

.. _sending_email:

Sending Email
=============

.. seealso:: `Postmark Send API <http://developer.postmarkapp.com/developer-build.html>`_
.. seealso:: :ref:`Sending Mail with the Simple API <simple_api_sending>`

.. _single_message:

Sending a single message
------------------------

To send a single message, create a :class:`Message` object, and pass it
to :func:`send`.

.. code-block:: python

    import pystmark

    API_KEY = 'my_api_key'
    SENDER = 'me@example.com'

    # Send a single message
    message = pystmark.Message(sender=SENDER, to='you@example.com',
                                   subject='Hi', text='A message',
                                   tag='greeting')

    pystmark.send(message, api_key=API_KEY)

You can also pass in a dictionary.  It will construct the :class:`Message`
for you.

.. code-block:: python

    import pystmark

    pystmark.send(dict(sender=SENDER, to='you@example.com', subject='Hi',
                       text='A message', tag='greeting'), api_key=API_KEY)

.. _batched_messages:

Sending batched messages
------------------------

This sends multiple messages in a single http request to Postmark's batch
send API.  There is a hard limit of 500 messages.

If you want to send the same message but to multiple recipients, you can
use :func:`send`, and construct the message with multiple `to`, `cc` or `bcc`
addresses. See :ref:`Multiple Recipients <multiple_recipients>`.

.. code-block:: python

    from pystmark import Message, send_batch

    # Send multiple messages (in one batched http request)
    recipients = ['you{0}@example.com'.format(i) for i in xrange(20)]
    messages = [Message(sender=SENDER, to=to, subject='Hi', text='A message',
                        tag='greeting') for to in recipients]

    response = send_batch(messages, api_key=API_KEY)

.. _multiple_recipients:

Multiple recipients
-------------------

The Postmark API allows you to have multiple `to` recipients. The total
number of recipients, including `to`, `cc`, and `bcc` is limited to 20.

.. code-block:: python

    from pystmark import Message, send

    message = Message(sender=SENDER, subject='Hi', text='A message',
                      to=['you@example.com', 'him@example.com'],
                      cc=['someone@example.com', 'her@example.com'],
                      bcc='user@example.com')

    send(message, api_key=API_KEY)

.. _sender_configuration:

Sender Configuration
--------------------

You can set defaults for your message sending using the
:ref:`advanced_api`.  For every method in the :ref:`simple_api`, there is a
corresponding configurable sender object in the :ref:`advanced_api`.

.. code-block:: python

    from pystmark import Message, Sender

    default_message = Message(sender=SENDER,
                              subject='Hi',
                              text='Welcome to the site',
                              html='<h1>Welcome to the site</h1>',
                              tag='greeting')

    sender = Sender(message=default_message, api_key=API_KEY)

    sender.send(dict(to='you@example.com'))

.. _attachments:

Attachments
-----------

Attachments are allowed, up to 10MB in size.  The attachment sizes are not
checked to be under the limit.  If you think you might go over the limit,
make sure to check yourself.  Only certain file extensions are allowed.

.. code-block:: python

    import pystmark

    filename = '/tmp/example.txt'
    with open(filename, 'w') as f:
        f.write('demo\n')

    message = pystmark.Message(sender='me@example.com',
                               to='you@example.com',
                               text='hi')

    # Attach using filename
    message.attach_file(filename)

    # Attach using binary
    with open(filename) as f:
        message.attach_binary(f.read(), filename)

    pystmark.send(message, api_key='the key')

.. _email_headers:

Email Headers
-------------

Custom headers can be added for your email.

.. code-block:: python

    import pystmark

    message = pystmark.Message(sender='me@example.com',
                               to='you@example.com',
                               text='hi')

    message.add_header('X-my-custom-header', 'foo')

    pystmark.send(message, api_key='the key')

.. _response_errors:

Response Errors
---------------

Some HTTP status codes will raise a custom Exception.
See :func:`Response.raise_for_status`.

.. code-block:: python

    from pystmark import send, UnauthorizedError

    r = send(dict(sender='me@example.com', to='you@example.com', text='hi'),
             api_key='bad key')

    try:
        r.raise_for_status()
    except UnauthorizedError:
        print 'Use your real API key'

.. request_args

Requests.request Arguments
--------------------------

If you need to pass some arguments to :func:`requests.request`, you can do so.
However, you cannot modify the `data` keyword.  It will be ignored if you
give it.

.. code-block:: python

    from pystmark import send, Message

    message = Message(sender='me@example.com', to='you@example.com', text='hi')

    send(message, api_key='my key', **dict(headers={'X-Something': 'foo'}))


.. bounce_handling_example:

Bounce Handling
===============

.. seealso:: `Postmark Bounce API <http://developer.postmarkapp.com/developer-bounces.html>`_
.. seealso:: :ref:`Bounce Handling with the Simple API <simple_api_bounce_handling>`

Retrieving bounced emails
-------------------------

Bounced emails are retrieved with :func:`get_bounces`.  The request must
be paginated with the `count` and `offset`.  They will default to 25 and 0,
respectively. If you provide a `message_id` (saved from the response of a
previously sent message), you do not need to provide `count` or `offset`.
You can filter bounces by a string match or bounce type.

.. code-block:: python

    from pystmark import send, get_bounces

    API_KEY = 'my key'

    # Get all bounces. If we do not paginate, 25 results will be returned at
    # offset 0.
    get_bounces(count=100, offset=0, api_key=API_KEY)

    # Get bounces of a specific type
    get_bounces(bounce_type='HardBounce', api_key=API_KEY)

    # Get bounces filtered by email string
    get_bounces(email_filter='@gmail.com', api_key=API_KEY)

    # Get bounces for a message
    r = send(dict(sender='me@example.com', to='you@example.com', text='hi'),
             api_key=API_KEY)
    get_bounces(message_id=r.message.id, api_key=API_KEY)


Retrieving a single bounce
--------------------------

Data for a single bounce can be retrieved given a `bounce_id`.

.. code-block:: python

    from pystmark import get_bounce, get_bounces

    r = get_bounces(api_key='my key')
    for bounce in r.bounces:
        get_bounce(bounce.id, api_key='my key')


Retrieving the raw dump for a single bounce
-------------------------------------------

The raw email dump can be retrieved with a `bounce_id` or with a
:class:`BouncedMessage`.

.. code-block:: python

    from pystmark import get_bounces, get_bounce_dump

    r = get_bounces(api_key='my key')
    for bounce in r.bounces:
        # Get dump via BouncedMessage.
        dump = bounce.dump(api_key='my key')
        # Get dump with the simple API
        dump = get_bounce_dump(bounce.id, api_key='my key')


Activating a bounced message (re-sending it)
--------------------------------------------

Bounces can be re-sent with activation.  Keep in mind that some bounces such
as hard bounces should be assumed dead.

.. code-block:: python

    from pystmark import get_bounces, activate_bounce

    r = get_bounces(api_key='my key')
    for bounce in r.bounces:
        activate_bounce(bounce.id)


Retrieving tags for bounced messages
------------------------------------

You can get a list of tags that have bounced messages.  Tags are set on the
message by you, when they are sent.

.. code-block:: python

    from pystmark import get_bounces, get_bounce_tags

    r = get_bounces(api_key='my key')
    for bounce in r.bounces:
        get_bounce_tags(bounce.id)


Retrieving delivery statistics
------------------------------

Delivery stats summarize your bounces.

.. code-block:: python

    from pystmark import get_delivery_stats

    r = get_delivery_stats(api_key='my key')
    print 'Inactive Messages:', r.inactive
    print 'Total bounces:', r.total
    print 'Bounces:'
    for bounce in r.bounces.values():
        print '\tType:', bounce.type
        print '\t\tName:', bounce.name
        print '\t\tCount:', bounce.count
