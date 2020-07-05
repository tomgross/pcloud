.. This README is meant for consumption by humans and pypi. Pypi can render rst files so please do not use Sphinx features.
   If you want to learn more about writing documentation, please check out: http://docs.plone.org/about/documentation_styleguide.html
   This text does not appear on pypi or github. It is a comment.

==============================================================================
pcloud - A Python API client for pCloud
==============================================================================

.. image:: https://travis-ci.org/tomgross/pycloud.svg?branch=master
    :target: https://travis-ci.org/tomgross/pycloud

This Python **(Version >= 3.6 only!)** library provides a Python API to the pCloud storage.

Features
--------

- Can be used as a library
- Comes with a command line script
- Provides a PyFileSystem implementation


Examples
--------

Usage of API

 >>> from pcloud import PyCloud
 >>> pc = PyCloud('email@example.com', 'SecretPassword')
 >>> pc.listfolder(folderid=0)

Usage of PyFilesystem with opener

 >>> from fs import opener
 >>> opener.open_fs('pcloud://email%40example.com:SecretPassword@/')
 <pCloudFS>

Uploading files

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


Documentation
-------------

Implements the pCloud API found at https://docs.pcloud.com/


Installation
------------

 $ pip install pcloud

Installation with PyFilesystem support

 $ bin/pip install pcloud[pyfs]

on zsh (Mac):

 $ bin/pip install "pcloud[pyfs]"

Contribute
----------

- Issue Tracker: https://github.com/tomgross/pycloud/issues
- Source Code: https://github.com/tomgross/pycloud


License
-------

The project is licensed under MIT (see docs/LICENSE.rst).
