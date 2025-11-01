==============================================================================
pcloud - A Python API client for pCloud
==============================================================================

.. image:: https://github.com/tomgross/pcloud/actions/workflows/pcloud-test.yml/badge.svg
    :target: https://github.com/tomgross/pcloud/actions

This Python **(Version >= 3.6 only!)** library provides a Python API to the pCloud storage.

Features
========

- Can be used as a library for accessing pCloud Features exposed by the officiall pCloud API

Examples
========

Usage of API
------------

 >>> from pcloud import PyCloud
 >>> pc = PyCloud('email@example.com', 'SecretPassword')
 >>> pc.listfolder(folderid=0)

Use alternate endpoints (*API calls have to be made to the correct API host name depending were the user has been
registered – api.pcloud.com for United States and eapi.pcloud.com for Europe.*)

 >>> from pcloud import PyCloud
 >>> pc = PyCloud('email@example.com', 'SecretPassword', endpoint="eapi")
 >>> pc.listfolder(folderid=0)

PyCloud also provides an API method to retrieve the nearest API server, which gives
you a speed gain for some API operations. To use PyCloud with this feature create
the PyCloud-object with the *nearest* endpoint parameter:

 >>> from pcloud import PyCloud
 >>> pc = PyCloud('email@example.com', 'SecretPassword', endpoint="nearest")
 >>> pc.listfolder(folderid=0)

Binary protocol
+++++++++++++++

pCloud supports JSON and binary format to access its API. By default
the Python pCloud API uses the JSON protocol. To make use of the
binary protocol you need to specify the according endpoints.

For United States server location:

 >>> pc = PyCloud('email@example.com', 'SecretPassword', endpoint="binapi")

For Europe server location:

 >>> pc = PyCloud('email@example.com', 'SecretPassword', endpoint="bineapi")

The API methods and parameters are identical for both protocols.

OAuth 2.0 authentication
------------------------

To use OAuth 2.0 authentication you need to create an App in pCloud (https://docs.pcloud.com/my_apps/).

Add the following redirect URI http://localhost:65432/
(Make sure port 65432 is available on your machine. Otherwise you need to adjust the `PORT` in oauth2.py)

Note! To see the redirect URI in the settings of pCloud you have to log out and log in again.

Once you finished adding the app and setting the redirect URI you are ready to use
OAuth 2.0 with PyCloud on your machine. For the communication with pCloud PyCloud uses the
builtin `webserver`-module. This means you need a real browser on your system available.

 >>> from pcloud import PyCloud
 >>> pc = PyCloud.oauth2_authorize(client_id="XYZ", client_secret="abc123")
 >>> pc.listfolder(folderid=0)

Headless mode
+++++++++++++

OAuth 2.0 is designed to use a browser for the authentication flow. Nevertheless Selenium
can be used to automate this process. For an example see the `pycloud_oauth2`-fixture in `test_oauth2.py`.
This method will not integrated as main functionality, since there are too many dependencies.
You can use it as example for your usecase.

Uploading files
---------------

a) from filenames:

  >>> pc.uploadfile(files=['/full/path/to/image1.jpg', '/Users/tom/another/image.png'],
  ...     path='/path-to-pcloud-dir')

b) from data:

  >>> import io
  >>> from PIL import Image
  >>> img = Image.open('image.jpg', 'r')
  >>> bio = io.BytesIO()
  >>> img.save(bio, format='jpeg')
  >>> pc.uploadfile(data=bio.getvalue(), filename="image.jpg", path='/path-to-pcloud-dir')

Downloading files
-----------------

Since the removal of the file API from pCloud downloading file content only via the
`getzip`- method. There was a convenience method added here to download files:

  >>> pc.file_download(fileid=1234567890)
  b'xxxx .... zzzz'


Searching files
---------------

The pCloud-API allows searching files, even this is not documented in the official
pCloud documentation.

  >>> pcapi.search(query="foo", offset=20, limit=10)

Known issues
============

- Some methods (like `listtokens`, `getzip`) are not usable when authenticated via OAuth2
  (see https://github.com/tomgross/pcloud/issues/61)
- Since the removal of file system operations from the pCloud API downloading files is 
  no longer supported when authenticated via OAuth2

Further Documentation
=====================

Implements the pCloud API found at https://docs.pcloud.com/


Installation
============

 $ pip install pcloud

Development
===========

For testing purposes a mock server is provided. To use this mock server
you need to add a file with the same name as the method + the `.json` suffix
in the tests/data directory (like `getdigest.json`).
The file contains the expected JSON result.

Contribute
==========

- Issue Tracker: https://github.com/tomgross/pcloud/issues
- Source Code: https://github.com/tomgross/pcloud

License
=======

The project is licensed under MIT (see LICENSE).

Contributors
============

- Tom Gross, itconsense@gmail.com
- Massimo Vannucci (blasterspike)
- Yennick Schepers (yennicks)
- olokelo
- qo4on

.. include:: CHANGES.rst
