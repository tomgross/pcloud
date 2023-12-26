import os
import unittest

from fs.path import abspath
from fs.test import FSTestCases
from pcloud.pcloudfs import PCloudFS


class TestMyFS(FSTestCases, unittest.TestCase):

    testdir = "_pyfs_tests"

    @classmethod
    def setUpClass(cls):
        username = os.environ.get("PCLOUD_USERNAME")
        password = os.environ.get("PCLOUD_PASSWORD")
        cls.pcloudfs = PCloudFS(username, password, endpoint="eapi")


    """
        @classmethod
        def tearDownClass(cls):
            cls.pcloudfs.removetree(cls.testdir)
    """

    def make_fs(self):
        # Return an instance of your FS object here
        return self.basedir
    
    def setUp(self):
        testdir = abspath(self.testdir)
        if self.pcloudfs.exists(testdir):
            self.pcloudfs.removetree(testdir)    
        self.basedir = self.pcloudfs.makedir(testdir)
        super().setUp()

    # override to not destroy filesystem
    def tearDown(self):
        self.pcloudfs.removetree(self.testdir)