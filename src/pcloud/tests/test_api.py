#
from pcloud import api

import os.path
import pytest


class DummyPyCloud(api.PyCloud):

    endpoint = "http://localhost:{0}/".format(5000)


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
