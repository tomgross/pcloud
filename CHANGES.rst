Changelog
=========

1.0a11 (unreleased)
-------------------

- Python 3.10 compatibility and dependency updates


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
  https://github.com/tomgross/pycloud/issues/10
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
