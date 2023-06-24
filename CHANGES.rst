Changelog
=========

1.2 (2023-06-24)
----------------

- Add `CONTRIBUTING` guideline and update `CODE_OF_CONDUCT` document [tomgross]
- Add Sonarcloud checker and report test coverage [tomgross]
- Add test for listtokens endpoint [tomgross]
- Changed repo name to https://github.com/tomgross/pcloud/ to be consistent (https://github.com/tomgross/pcloud/issues/70) [tomgross]
- Implement `sharefolder`-endpoint [tomgross]
- Replace ``cgi.FieldStorage`` by ``multipart`` avoiding
  the ``cgi`` module deprecated by Python 3.11. [tomgross]

1.1 (2022-11-14)
----------------

- Fix upload with int folderid #63 [tomgross]
- Add pytest timeout and update testing dependencies [tomgross]
- Implement `copyfile` and `downloadfileasync` methods [tomgross]
- Implement `setlanguage`, `getfeedback`, `diff` & `getfilehistory` methods [tomgross]


1.0 (2022-02-02)
----------------

- 🎉 Release unchanged as 1.0 🎉

1.0b2 (2021-12-17)
------------------

- Build wheel package [tomgross]
- Fix file upload with oauth [giust]
- Automated test for OAuth [tomgross]
- Documented headless OAuth [tomgross]

1.0b1 (2021-11-26)
------------------

- Python 3.10 compatibility and dependency updates
- Change port of test server 5000 -> 5023
- Add *getpubzip* API method (https://github.com/tomgross/pcloud/issues/51)
- Allow uploading BIG files by using MultipartEncoder of requests_toolbelt
  (https://github.com/tomgross/pcloud/issues/25, https://github.com/tomgross/pcloud/issues/44)
- Log login process
  [tomgross]

1.0a10 (2021-07-11)
-------------------

- State and test Python 3.9 support [tomgross]
- OAuth 2.0 implementation [tomgross]
- Implement more general methods [tomgross]
- Implement get nearest api server [tomgross]

1.0a9 (2021-01-22)
------------------

- Missing variable in output in case a directory already exists
- Changed errors raised for makedirs
- Do not raise an errors.DirectoryExists when recreate = True
- Added examples to README
  [blasterspike]

- Fix parameter of downloadlink method
  [tomgross]

- Add more details on authentication error
  [yennicks]

- Add new stats endpoint
  [AgusRumayor]

- Add methods for archiving
  [olokelo]

- Add token expire parameter
  [olekelo]

- Start implementing trash methods
  [qo4on, tomgross]

- Add support for alternate endpoints
  [tomgross]

- Add Contributors and fix README ReST Syntax

1.0a8 (2020-02-21)
------------------

- Fix upload of multiple files from paths
  [tomgross]

- Document uploading of files
  [tomgross]

1.0a7 (2020-02-20)
------------------

- Add new API method `createfolderifnotexists` #19
  [Arkoniak, tomgross]

- Fix duplication of data transfer on file upload #17
  [blasterspike, tomgross]

- Consistently use MIT licences
  [tomgross]

1.0a6 (2019-01-18)
------------------

- Fix error while using makedirs from PyFilesystem with recreate=True
  [blasterspike]

1.0a5 (2018-10-22)
------------------

- Fix error while using makedirs from PyFilesystem
  https://github.com/tomgross/pcloud/issues/10
  [blasterspike]

- Test and claim Python 3.7 compatibility
  [tomgross]

1.0a4 (2017-10-29)
------------------

- Fix error with duplicate files parameter #3
  [tomgross]

- Fix upload of data
  [tomgross]

- Do flake8 checks
  [tomgross]


1.0a3 (2017-10-07)
------------------

- Test API with py.test
  [tomgross]

- Support for PyFileSystem
  [tomgross]

- Support for file operations
  [tomgross]

1.0a2 (2017-05-21)
------------------

- Rename to pcloud
  [tomgross]


1.0a1 (2017-05-21)
------------------

- Initial release.
  [tomgross]
