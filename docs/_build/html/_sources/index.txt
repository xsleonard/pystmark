Pystmark
=======

.. module:: pystmark

Pystmark is a wrapper around the Postmark API. It is built on top of
Python Requests.

.. _pystmark: https://github.com/xsleonard/pystmark
.. _Requests: https://github.com/kennethreitz/requests


Installation
------------
Install the extension with one of the following commands::

    $ easy_install pystmark

or alternatively if you have pip installed::

    $ pip install pystmark


Usage
-----

Ensure that Python Requests is installed.

API
---

Sender
------------------

.. autoclass:: pystmark.PystSender
    :members:

Batch Sender
-----------------------

.. autoclass:: pystmark.PystBatchSender
    :members:

Bounce Handler
-------------

.. autoclass:: pystmark.PystBounceHandler
    :members:
