#
from pcloud import api
from pcloud.pcloudfs import PCloudFS

import datetime
import json
import os.path
import pytest


class NoOpSession(object):
    kwargs = {}

    def get(self, url, **kwargs):
        self.kwargs = kwargs
        self.kwargs["url"] = url
        return self

    def json(self):
        return self.kwargs


class DummyPyCloud(api.PyCloud):
    noop = False

    def get_auth_token(self):
        if self.noop:
            self.auth_token = None
            self.access_token = None
        else:
            return super(DummyPyCloud, self).get_auth_token()

    def __init__(self, username, password, noop=False):
        if noop:
            self.noop = True
        super(DummyPyCloud, self).__init__(username, password, endpoint="test")
        if noop:
            self.session = NoOpSession()


class DummyPCloudFS(PCloudFS):
    factory = DummyPyCloud


def test_getfolderpublink():
    api = DummyPyCloud("john", "doe", noop=True)
    dt = datetime.datetime(2023, 10, 5, 12, 3, 12)
    assert api.getfolderpublink(folderid=20, expire=dt) == {
        "params": {"expire": "2023-10-05T12:03:12", "folderid": 20},
        "url": "http://localhost:5023/getfolderpublink",
    }


@pytest.mark.usefixtures("start_mock_server")
class TestPcloudApi(object):
    noop_dummy_file = "/test.txt"

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

    def test_upload_files_int_folderid(self):
        api = DummyPyCloud("foo", "bar")
        testfile = os.path.join(os.path.dirname(__file__), "data", "upload.txt")
        assert api.uploadfile(files=[testfile], folderid=0) == {
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
            papi.getfilelink(file=self.noop_dummy_file)

    def test_getvideolink(self):
        papi = DummyPyCloud("foo", "bar")
        with pytest.raises(api.OnlyPcloudError):
            papi.getvideolink(file=self.noop_dummy_file)

    def test_getvideolinks(self):
        papi = DummyPyCloud("foo", "bar")
        with pytest.raises(api.OnlyPcloudError):
            papi.getvideolinks(file=self.noop_dummy_file)

    def test_getfilepublink(self):
        papi = DummyPyCloud("foo", "bar")
        with pytest.raises(api.OnlyPcloudError):
            papi.getfilepublink(file=self.noop_dummy_file)

    def test_getpublinkdownload(self):
        papi = DummyPyCloud("foo", "bar")
        with pytest.raises(api.OnlyPcloudError):
            papi.getpublinkdownload(file=self.noop_dummy_file)

    def test_server_security(self):
        api = DummyPyCloud("", "")
        resp = api.session.get(api.endpoint + "../../bogus.sh", params={})
        assert resp.content == b'{"Error": "Path not found or not accessible!"}'
        assert resp.status_code == 404
