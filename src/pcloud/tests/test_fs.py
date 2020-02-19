from pcloud.pcloudfs import PCloudFS
from pcloud.tests.test_api import DummyPyCloud

import pytest


class DummyPCloudFS(PCloudFS):

    factory = DummyPyCloud


@pytest.mark.usefixtures("start_mock_server")
class TestPcloudFs(object):
    def test_write(self):
        with DummyPCloudFS(username="foo", password="bar") as fs:

            #  testfile = os.path.join(os.path.dirname(__file__), 'data', 'upload.txt')
            # assert api.uploadfile(files=[testfile]) == {"result": 0,
            #
            #                                           "metadata": {"size": 14}}
            data = b"hello unittest"
            fs_f = fs.openbin("hello.bin")
            foo = fs_f.write(data)
            # import pdb; pdb.set_trace()
            assert True
