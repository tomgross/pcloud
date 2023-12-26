==============================================================================
pcloud - A Python API client for pCloud
==============================================================================

.. image:: https://github.com/tomgross/pcloud/actions/workflows/pcloud-test.yml/badge.svg
    :target: https://github.com/tomgross/pcloud/actions

This Python **(Version >= 3.6 only!)** library provides a Python API to the pCloud storage.

Features
========

- Can be used as a library
- Provides a PyFileSystem implementation

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

Usage of PyFilesystem with opener

  >>> from fs import opener
  >>> opener.open_fs('pcloud://email%40example.com:SecretPassword@/')
  <pCloudFS>

Copying files from Linux to pCloud using PyFilesystem

  >>> from fs import opener, copy
  >>> with opener.open_fs('pcloud://email%40example.com:SecretPassword@/') as pcloud_fs:
  >>>    with opener.open_fs('/opt/data_to_copy') as linux_fs:
  >>>        copy.copy_file(src_fs=linux_fs,
  >>>                       src_path='database.sqlite3',
  >>>                       dst_fs=pcloud_fs,
  >>>                       dst_path='/backup/server/database.sqlite3')

Copy directory from Linux to pCloud using PyFilesystem

  >>> from fs import opener, copy
  >>> with opener.open_fs('pcloud://email%40example.com:SecretPassword@/') as pcloud_fs:
  >>>    with opener.open_fs('/opt/data_to_copy') as linux_fs:
  >>>        copy.copy_dir(src_fs=linux_fs,
  >>>                      src_path='database/',
  >>>                      dst_fs=pcloud_fs,
  >>>                      dst_path='/backup/database/')

Further Documentation
=====================

Implements the pCloud API found at https://docs.pcloud.com/


Installation
============

 $ pip install pcloud

Installation with PyFilesystem support

 $ bin/pip install pcloud[pyfs]

on zsh (Mac):

 $ bin/pip install "pcloud[pyfs]"


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
