import os
import pytest
import time
import zipfile

from io import BytesIO
from pathlib import Path
from pcloud.api import PyCloud
from pcloud.api import O_CREAT


@pytest.fixture
def pycloud():
    username = os.environ.get("PCLOUD_USERNAME")
    password = os.environ.get("PCLOUD_PASSWORD")
    return PyCloud(username, password, endpoint="eapi")


folder_for_tests = "integration-test"
# upload `data/upload.txt` to integration test instance,
# generate a public link (code) and insert the code below.
# Generating public links with the API is currently not possible.
public_code = "XZ0UCJZ5o9LaCgvhDQq9LD7GXrx40pSsRoV"


@pytest.fixture
def testfolder(pycloud):
    pycloud.createfolder(folderid=0, name=folder_for_tests)
    yield folder_for_tests
    pycloud.deletefolderrecursive(path=f"/{folder_for_tests}")


def test_login(pycloud):
    ui = pycloud.userinfo()
    assert ui["email"] == os.environ.get("PCLOUD_USERNAME")


def test_upload_download_roundrobin(pycloud, testfolder):
    testfile = testfile = Path(__file__).parent / "data" / "upload.txt"
    result = pycloud.uploadfile(path=f"/{testfolder}", files=[testfile])
    size = result["metadata"][0]["size"]
    assert result["result"] == 0
    assert size == 14
    fd = pycloud.file_open(path=f"/{folder_for_tests}/upload.txt", flags=O_CREAT)["fd"]
    result = pycloud.file_read(fd=fd, count=size)
    with open(testfile) as f:
        assert result == bytes(f.read(), "utf-8")
    result = pycloud.file_close(fd=fd)
    assert result["result"] == 0


def test_publink_zip_with_unzip(pycloud):
    result = pycloud.getpubzip(code=public_code, unzip=True)
    assert result == b"Hello pCloud!\n"


def test_publink_zip(pycloud):
    zipresponse = pycloud.getpubzip(code=public_code)
    # I'm not sure, if zipping is deterministic,
    # so let's only check, if we find a valid ZIP file
    zipfmem = BytesIO(zipresponse)
    zf = zipfile.ZipFile(zipfmem)
    result_code = zf.testzip()
    assert result_code is None


def test_copyfile(pycloud, testfolder):
    testfilename = "Getting started with pCloud.pdf"
    tofilename = f"/{folder_for_tests}/{testfilename}"
    resp = pycloud.copyfile(path=f"/{testfilename}", topath=tofilename)
    assert resp["result"] == 0
    time.sleep(1)
    resp = pycloud.checksumfile(path=tofilename)
    assert (
        resp.get("sha256")
        == "df745d42f69266c49141ea7270c45240cf883b9cdb6a14fffcdff33c04c5304c"
    ), f"Failure with checksum in {resp}"


def test_listtokens(pycloud):
    result = pycloud.listtokens()
    assert result["result"] == 0
    assert len(result["tokens"]) > 1
