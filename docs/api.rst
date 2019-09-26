.. include:: simple_api.rst.inc
.. include:: advanced_api.rst.inc

.. _message_object:

Message Object
==============

.. autoclass:: pystmark.Message
    :inherited-members:

.. _response_objects:

Response Objects
================

.. autoclass:: pystmark.SendResponse

.. autoclass:: pystmark.BatchSendResponse

.. autoclass:: pystmark.BouncesResponse

.. autoclass:: pystmark.BounceResponse

.. autoclass:: pystmark.BounceDumpResponse

.. autoclass:: pystmark.BounceActivateResponse

.. autoclass:: pystmark.BounceTagsResponse

.. autoclass:: pystmark.DeliveryStatsResponse

.. autoclass:: pystmark.OutboundMessageDetailsResponse


.. _response_data_wrappers:

Response Data Wrappers
======================

.. autoclass:: pystmark.MessageConfirmation
    :inherited-members:

.. autoclass:: pystmark.BouncedMessage
    :inherited-members:

.. autoclass:: pystmark.BounceTypeData
    :inherited-members:

.. _exceptions:

Exceptions
==========

.. autoclass:: pystmark.PystmarkError
    :inherited-members:

.. autoclass:: pystmark.MessageError
    :inherited-members:

.. autoclass:: pystmark.BounceError
    :inherited-members:

.. autoclass:: pystmark.ResponseError
    :inherited-members:

.. autoclass:: pystmark.UnauthorizedError
    :inherited-members:

.. autoclass:: pystmark.UnprocessableEntityError
    :inherited-members:

.. autoclass:: pystmark.InternalServerError
    :inherited-members:


.. _base_classes:

Base Classes
============

.. autoclass:: pystmark.Interface
    :inherited-members:

.. autoclass:: pystmark.Response
    :inherited-members:
