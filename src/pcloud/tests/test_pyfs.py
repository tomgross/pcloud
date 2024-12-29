import os
import unittest
import uuid

from fs import errors
from fs.test import FSTestCases
from fs import opener
from pcloud.pcloudfs import PCloudFS
from urllib.parse import quote


class TestpCloudFS(FSTestCases, unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        username = os.environ.get("PCLOUD_USERNAME")
        password = os.environ.get("PCLOUD_PASSWORD")
        cls.pcloudfs = PCloudFS(username, password, endpoint="eapi")

    def make_fs(self):
        # Return an instance of your FS object here
        # For some unknown (concurrency?) reason we can't use
        # opendir not directly as it fails with a RessourceNotFound exception
        # we create a subfs object directly.
        return self.pcloudfs.subfs_class(self.pcloudfs, self.testdir)

    def _prepare_testdir(self):
        random_uuid = uuid.uuid4()
        testdir = f"/_pyfs_tests_{random_uuid}"
        resp = self.pcloudfs.pcloud.createfolder(path=testdir)
        assert resp["result"] == 0
        self.testdir = resp["metadata"]["path"]
        self.testdirid = resp["metadata"]["folderid"]

    def setUp(self):
        self._prepare_testdir()
        super().setUp()

    # override to not destroy filesystem
    def tearDown(self):
        self.pcloudfs.pcloud.deletefolderrecursive(folderid=self.testdirid)

    # This is a literal copy of the test_remove test of the FSTestCases
    # without using the deprecated 'assertRaisesRegexp',
    # which was removed in Python 3.12.
    # Remove this method once this is fixed in the 'fs'-package itself
    def test_remove(self):
        self.fs.writebytes("foo1", b"test1")
        self.fs.writebytes("foo2", b"test2")
        self.fs.writebytes("foo3", b"test3")

        self.assert_isfile("foo1")
        self.assert_isfile("foo2")
        self.assert_isfile("foo3")

        self.fs.remove("foo2")

        self.assert_isfile("foo1")
        self.assert_not_exists("foo2")
        self.assert_isfile("foo3")

        with self.assertRaises(errors.ResourceNotFound):
            self.fs.remove("bar")

        self.fs.makedir("dir")
        with self.assertRaises(errors.FileExpected):
            self.fs.remove("dir")

        self.fs.makedirs("foo/bar/baz/")

        error_msg = "resource 'foo/bar/egg/test.txt' not found"
        with self.assertRaisesRegex(errors.ResourceNotFound, error_msg):
            self.fs.remove("foo/bar/egg/test.txt")

    # Test custom functionality

    def test_fs_opener(self):
        username = quote(os.environ.get("PCLOUD_USERNAME"))
        password = os.environ.get("PCLOUD_PASSWORD")
        with opener.open_fs(f"pcloud+eapi://{username}:{password}@/") as pcloud_fs:
            assert pcloud_fs.pcloud.endpoint == "https://eapi.pcloud.com/"
