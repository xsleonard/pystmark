.. _api:

.. module:: pystmark

Simple API
==========

.. autofunction:: pystmark.send
.. autofunction:: pystmark.send_batch
.. autofunction:: pystmark.get_bounces
.. autofunction:: pystmark.get_bounce
.. autofunction:: pystmark.get_bounce_dump
.. autofunction:: pystmark.activate_bounce
.. autofunction:: pystmark.get_bounce_tags
.. autofunction:: pystmark.get_delivery_stats


Advanced API
============


Sending Email
-------------

.. autoclass:: pystmark.PystSender
    :inherited-members:

.. autoclass:: pystmark.PystBatchSender
    :inherited-members:


Bounce Retrieval API
--------------------

.. autoclass:: pystmark.PystBounces
    :inherited-members:

.. autoclass:: pystmark.PystBounce
    :inherited-members:

.. autoclass:: pystmark.PystBounceDump
    :inherited-members:

.. autoclass:: pystmark.PystBounceActivate
    :inherited-members:

.. autoclass:: pystmark.PystBounceTags
    :inherited-members:

.. autoclass:: pystmark.PystDeliveryStats
    :inherited-members:


Response Objects
----------------

.. autoclass:: pystmark.PystSendResponse
    :inherited-members:

.. autoclass:: pystmark.PystBouncesResponse
    :inherited-members:

.. autoclass:: pystmark.PystBounceResponse
    :inherited-members:

.. autoclass:: pystmark.PystBounceDumpResponse
    :inherited-members:

.. autoclass:: pystmark.PystBounceActivateResponse
    :inherited-members:

.. autoclass:: pystmark.PystBounceTagsResponse
    :inherited-members:

.. autoclass:: pystmark.PystDeliveryStatsResponse
    :inherited-members:


Message Objects
---------------

.. autoclass:: pystmark.PystMessage
    :inherited-members:

.. autoclass:: pystmark.PystBouncedMessage
    :inherited-members:


Exceptions
----------

.. autoclass:: pystmark.PystMessageError
    :inherited-members:

.. autoclass:: pystmark.PystBounceError
    :inherited-members:

.. autoclass:: pystmark.PystUnauthorizedError
    :inherited-members:

.. autoclass:: pystmark.PystUnprocessableEntityError
    :inherited-members:

.. autoclass:: pystmark.PystInternalServerError
    :inherited-members:


Base Classes
------------

.. autoclass:: pystmark.PystInterface
    :inherited-members:

.. autoclass:: pystmark.PystResponse
    :inherited-members:
