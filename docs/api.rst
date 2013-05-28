.. include:: simple_api.rst.inc
.. include:: advanced_api.rst.inc

.. _message_object:

Message Object
==============

.. autoclass:: pystmark.PystMessage
    :inherited-members:

.. _response_objects:

Response Objects
================

.. autoclass:: pystmark.PystSendResponse

.. autoclass:: pystmark.PystBatchSendResponse

.. autoclass:: pystmark.PystBouncesResponse

.. autoclass:: pystmark.PystBounceResponse

.. autoclass:: pystmark.PystBounceDumpResponse

.. autoclass:: pystmark.PystBounceActivateResponse

.. autoclass:: pystmark.PystBounceTagsResponse

.. autoclass:: pystmark.PystDeliveryStatsResponse


.. _response_data_wrappers:

Response Data Wrappers
======================

.. autoclass:: pystmark.PystMessageConfirmation
    :inherited-members:

.. autoclass:: pystmark.PystBouncedMessage
    :inherited-members:

.. autoclass:: pystmark.PystBounceTypeData
    :inherited-members:

.. _exceptions:

Exceptions
==========

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


.. _base_classes:

Base Classes
============

.. autoclass:: pystmark.PystInterface
    :inherited-members:

.. autoclass:: pystmark.PystResponse
    :inherited-members:
