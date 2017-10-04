.. This README is meant for consumption by humans and pypi. Pypi can render rst files so please do not use Sphinx features.
   If you want to learn more about writing documentation, please check out: http://docs.plone.org/about/documentation_styleguide.html
   This text does not appear on pypi or github. It is a comment.

==============================================================================
pcloud - A Python API client for pCloud
==============================================================================

.. image:: https://travis-ci.org/tomgross/pycloud.svg?branch=master
    :target: https://travis-ci.org/tomgross/pycloud

This Python library provides a Python API to the pCloud storage.

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


Documentation
-------------

Implements the pCloud API found at https://docs.pcloud.com/


Installation
------------

 $ pip install pcloud

Contribute
----------

- Issue Tracker: https://github.com/tomgross/pycloud/issues
- Source Code: https://github.com/tomgross/pycloud


License
-------

The project is licensed under the GPLv2.
