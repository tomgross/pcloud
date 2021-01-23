#
from pcloud import api
from pcloud.pcloudfs import PCloudFS

import json
import os.path
import pytest


class DummyPyCloud(api.PyCloud):
    def __init__(self, username, password):
        super(DummyPyCloud, self).__init__(username, password, endpoint="test")


class DummyPCloudFS(PCloudFS):

    factory = DummyPyCloud


@pytest.mark.usefixtures("start_mock_server")
class TestPcloudApi(object):
    def test_getdigest(self):
        api = DummyPyCloud("foo", "bar")
        assert api.getdigest() == b"YGtAxbUpI85Zvs7lC7Z62rBwv907TBXhV2L867Hkh"

    def test_get_auth_token(self):
        api = DummyPyCloud("foo", "bar")
        assert api.get_auth_token() == "TOKEN"

    def test_upload_files(self):
        api = DummyPyCloud("foo", "bar")
        testfile = os.path.join(os.path.dirname(__file__), "data", "upload.txt")
        assert api.uploadfile(files=[testfile]) == {
            "result": 0,
            "metadata": {"size": 14},
        }

    def test_extractarchive(self):
        api = DummyPyCloud("foo", "bar")
        testfile = os.path.join(
            os.path.dirname(__file__), "data", "extractarchive.json"
        )
        with open(testfile) as f:
            expected = json.load(f)
            assert api.extractarchive(fileid=999, topath="/unittest") == expected

    def test_getfilelink(self):
        papi = DummyPyCloud("foo", "bar")
        with pytest.raises(api.OnlyPcloudError):
            papi.getfilelink(file="/test.txt")


@pytest.mark.usefixtures("start_mock_server")
class TestPcloudFs(object):
    def test_write(self, capsys):
        with DummyPCloudFS(username="foo", password="bar") as fs:
            data = b"hello pcloud fs unittest"
            fs_f = fs.openbin("hello.bin")
            fs_f.write(data)
            captured = capsys.readouterr()
            assert captured.out == "File: b'hello pcloud fs unittest', Size: 24"
