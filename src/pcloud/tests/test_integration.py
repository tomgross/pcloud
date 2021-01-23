import os
from pcloud.api import PyCloud
from pcloud.api import O_CREAT


class TestIntegration(object):

    folder_for_tests = "integration-test"

    def setup_method(self):
        """"""
        self.username = os.environ.get("PCLOUD_USERNAME")
        password = os.environ.get("PCLOUD_PASSWORD")
        self.pc = PyCloud(self.username, password, endpoint="eapi")
        self.pc.createfolder(folderid=0, name=self.folder_for_tests)

    def teardown_method(self):
        """ """
        self.pc.deletefolderrecursive(path=f"/{self.folder_for_tests}")

    def test_login(self):
        ui = self.pc.userinfo()
        assert ui["email"] == self.username

    def test_upload_download_roundrobin(self):
        testfile = os.path.join(os.path.dirname(__file__), "data", "upload.txt")
        result = self.pc.uploadfile(path=f"/{self.folder_for_tests}", files=[testfile])
        size = result["metadata"][0]["size"]
        assert result["result"] == 0
        assert size == 14
        fd = self.pc.file_open(
            path=f"/{self.folder_for_tests}/upload.txt", flags=O_CREAT
        )["fd"]
        result = self.pc.file_read(fd=fd, count=size)
        with open(testfile) as f:
            assert result == bytes(f.read(), "utf-8")
        result = self.pc.file_close(fd=fd)
        assert result["result"] == 0
