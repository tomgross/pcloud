import os
import unittest
import uuid

from fs.errors import ResourceNotFound
from fs.path import abspath
from fs.test import FSTestCases
from pcloud.pcloudfs import PCloudFS


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
        testdir = f'/_pyfs_tests_{random_uuid}'
        self.pcloudfs.pcloud.createfolder(path=testdir)
        self.testdir = testdir

    def setUp(self):
        self._prepare_testdir()
        super().setUp()

    # override to not destroy filesystem
    def tearDown(self):
        try:
            self.pcloudfs.removetree(self.testdir)
        except ResourceNotFound:  # pragma: no coverage
            pass