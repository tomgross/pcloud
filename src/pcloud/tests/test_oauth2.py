import os
import pytest

from pathlib import Path
from pcloud.api import PyCloud
from pcloud.api import O_CREAT


folder_for_tests = "integration-test"


@pytest.fixture
def pycloud_oauth2():
    access_token = os.environ.get("PCLOUD_OAUTH2_TOKEN")
    return PyCloud("", access_token, endpoint="eapi", oauth2=True)


@pytest.fixture
def testfolder(pycloud_oauth2):
    pycloud_oauth2.createfolder(folderid=0, name=folder_for_tests)
    yield folder_for_tests
    pycloud_oauth2.deletefolderrecursive(path=f"/{folder_for_tests}")


def test_upload_download_roundrobin(pycloud_oauth2, testfolder):
    testfile = testfile = Path(__file__).parent / "data" / "upload.txt"
    result = pycloud_oauth2.uploadfile(path=f"/{testfolder}", files=[testfile])
    size = result["metadata"][0]["size"]
    assert result["result"] == 0
    assert size == 14
    fd = pycloud_oauth2.file_open(path=f"/{folder_for_tests}/upload.txt", flags=O_CREAT)["fd"]
    result = pycloud_oauth2.file_read(fd=fd, count=size)
    with open(testfile) as f:
        assert result == bytes(f.read(), "utf-8")
    result = pycloud_oauth2.file_close(fd=fd)
    assert result["result"] == 0
