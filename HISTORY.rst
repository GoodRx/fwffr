=======
History
=======

0.5.0 (2021-02-10)
------------------

**BREAKING**: Removed ``message`` attribute on exceptions. This was deprecated
in Python 2.6 and was causing crashes on Python 3.

New
~~~

* Added official support for Python 3.6 - 3.10.
* Arguments to exceptions are now preserved as attributes to ease debugging.
* More documentation.
* Upgraded development status from "pre-alpha" to "stable".

Bugfixes
~~~~~~~~

* Fixed `issue 2`_
* Removed erroneous trove classifier for NLP
* Added missing ``python_requires`` directive
* Fixed test suite that wasn't running due to an invalid import

0.1.0 (2017-08-30)
------------------

* First release on PyPI.

.. _issue 2: https://github.com/GoodRx/fwffr/issues/2
