import os
import tenacity
import unittest

from fs.errors import ResourceNotFound
from fs.path import abspath
from fs.test import FSTestCases
from pcloud.pcloudfs import PCloudFS


class TestpCloudFS(FSTestCases, unittest.TestCase):

    testdir = "_pyfs_tests"

    @classmethod
    def setUpClass(cls):
        username = os.environ.get("PCLOUD_USERNAME")
        password = os.environ.get("PCLOUD_PASSWORD")
        cls.pcloudfs = PCloudFS(username, password, endpoint="eapi")

    def make_fs(self):
        # Return an instance of your FS object here
        return self.basefs
    
    @tenacity.retry(
        stop=tenacity.stop_after_attempt(2),    
        retry=tenacity.retry_if_exception_type(ResourceNotFound),
        wait=tenacity.wait_incrementing(1, 2, 3),
        reraise=True
    )
    def _prepare_basedir(self):
        testdir = abspath(self.testdir)
        try:
            if self.pcloudfs.exists(testdir):
                self.pcloudfs.removetree(testdir)
        except ResourceNotFound:  # pragma: no coverage
            pass
        # use api method directly, since `makedir` checks the
        # basepath and prevents creating here
        resp = self.pcloudfs.pcloud.createfolder(path=testdir)
        result = resp["result"]
        if result == 0:
            return self.pcloudfs.opendir(testdir)
        else:
            raise ResourceNotFound(testdir)
        # return self.pcloudfs.makedir(testdir, recreate=True)

    def setUp(self):
        self.basefs = self._prepare_basedir()
        super().setUp()

    # override to not destroy filesystem
    def tearDown(self):
        try:
            self.pcloudfs.removetree(self.testdir)
        except ResourceNotFound:  # pragma: no coverage
            pass