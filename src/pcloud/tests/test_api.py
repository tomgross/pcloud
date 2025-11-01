#
from pcloud import api
from pcloud.dummyprotocol import NoOpSession

import datetime
import json
import logging
import os.path
import pytest
import httpx


class DummyPyCloud(api.PyCloud):
    noop = False

    def get_auth_token(self):
        if self.noop:
            self.auth_token = None
            self.access_token = None
        else:
            return super().get_auth_token()

    def __init__(self, username, password, noop=False):
        if noop:
            self.noop = True
        super().__init__(username, password, endpoint="test")
        if noop:
            self.session = NoOpSession()

    def _do_request(self, method, authenticate=True, json=True, endpoint=None, **kw):
        if self.noop:
            kw["noop"] = True
        return self.connection.do_get_request(
            method, authenticate, json, endpoint, **kw
        )


def test_getfolderpublink():
    pcapi = DummyPyCloud("john", "doe", noop=True)
    dt = datetime.datetime(2023, 10, 5, 12, 3, 12)
    assert pcapi.getfolderpublink(folderid=20, expire=dt) == {
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

    def test_getaudiolink(self):
        papi = DummyPyCloud("foo", "bar")
        with pytest.raises(api.OnlyPcloudError):
            papi.getaudiolink()

    def test_gethlslink(self):
        papi = DummyPyCloud("foo", "bar")
        with pytest.raises(api.OnlyPcloudError):
            papi.gethlslink()

    def test_gettextfile(self):
        papi = DummyPyCloud("foo", "bar")
        with pytest.raises(api.OnlyPcloudError):
            papi.gettextfile()

    def test_server_security(self):
        papi = DummyPyCloud("", "")
        resp = httpx.get(papi.endpoint + "../../bogus.sh", params={})
        assert resp.content == b'{"Error": "Path not found or not accessible!"}'
        assert resp.status_code == 404

    def test_copypubfile(self):
        papi = DummyPyCloud("", "")
        result = papi.copypubfile(code="xyz", noop=True)
        assert result == {'params': {'code': 'xyz'}, 'url': 'http://localhost:5023/copypubfile'}

    def test_deletepublink(self):
        papi = DummyPyCloud("", "")
        result = papi.deletepublink(linkid="123", noop=True)
        assert result == {'params': {'linkid': '123'}, 'url': 'http://localhost:5023/deletepublink'}

    def test_changepublink(self):
        papi = DummyPyCloud("", "")
        result = papi.changepublink(linkid="1234", noop=True)
        assert result == {'params': {'linkid': '1234'}, 'url': 'http://localhost:5023/changepublink'}

    def test_getnearestendpoint(self):
        papi = DummyPyCloud("", "", noop=True)
        assert papi.getnearestendpoint() == 'https://api.pcloud.com/'

    def test_invalidendpoint(self, caplog):
        with caplog.at_level(logging.ERROR):
            api.PyCloud("", "", endpoint="bogus")
        assert caplog.records[0].message == "Endpoint (bogus) not found. Use one of: api, eapi, test, binapi, bineapi, nearest"

    def test_file_download_invalid(self):
        papi = DummyPyCloud("", "")
        with pytest.raises(OSError):
            papi.file_download(fileid=345, result=2055, error="Not found", noop=True)

