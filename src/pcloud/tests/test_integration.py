import os
import pytest
import time
import zipfile

from io import BytesIO
from pathlib import Path
from pcloud.api import PyCloud
from urllib.parse import quote


@pytest.fixture(scope="module", params=["eapi", "bineapi"])
def pycloud(request):
    username = os.environ.get("PCLOUD_USERNAME")
    password = os.environ.get("PCLOUD_PASSWORD")
    return PyCloud(username, password, endpoint=request.param)


testfilename = "Getting started with pCloud.pdf"
folder_for_tests = "integration-test"
# upload `data/upload.txt` to integration test instance,
# generate a public link (code) and insert the code below.
# Generating public links with the API is currently not possible.
public_filename = "publink_testfile.txt"
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
    download_data = pycloud.file_download(fileid=result["metadata"][0]["fileid"])
    with open(testfile, "r") as tf:
        assert  bytes(tf.read(), "utf-8") == download_data


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
    # First, copy public file to our test folder since "Getting started with pCloud.pdf" 
    # is NOT the same on every account
    pycloud.copypubfile(code=public_code, topath=f"/{folder_for_tests}/{public_filename}")
    time.sleep(1)

    tofilename = f"/{folder_for_tests}/{testfilename}"
    resp = pycloud.copyfile(path=f"/{folder_for_tests}/{public_filename}", topath=tofilename)
    assert resp["result"] == 0
    time.sleep(1)
    resp = pycloud.checksumfile(path=tofilename)
    # Updated checksum to match current version of the file
    assert (
        resp.get("sha256")
        == "3ee91667abf68bfbf99462eed263a2458173d63c175fdf26f0580b9b49f9cdb7"
    ), f"Failure with checksum in {resp}"


def test_search(pycloud):
    resp = pycloud.search(query=testfilename, limit=1)
    assert len(resp["items"]) == 1
    assert resp["items"][0]["name"] == testfilename


def test_fileexists_true(pycloud):
    assert pycloud.file_exists(path=f"/{testfilename}")


def test_fileexists_false(pycloud):
    assert pycloud.file_exists(path="/bogusfile.txt") == False


def test_listtokens(pycloud):
    result = pycloud.listtokens()
    assert result["result"] == 0
    assert len(result["tokens"]) > 1
