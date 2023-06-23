import os
import pytest

from pathlib import Path
from pcloud.api import PyCloud
from pcloud.api import log
from pcloud.api import O_CREAT
from pcloud.oauth2 import TokenHandler

from playwright.sync_api import sync_playwright, expect


folder_for_tests = "integration-test"


class PlaywrightTokenHandler(TokenHandler):
    """
    Class used to handle pClouds oAuth2 via playwright browser
    """

    def open_browser(self):
        with sync_playwright() as p:
            self.browser = p.firefox.launch()
            page = self.browser.new_page()
            log.info(self.auth_url)
            page.goto(self.auth_url)
            page.get_by_placeholder("Email").fill(os.environ.get("PCLOUD_USERNAME"))
            page.get_by_text("Continue").click()
            page.get_by_placeholder("Password").fill(os.environ.get("PCLOUD_PASSWORD"))
            page.get_by_text("Log in").click()
            expect(page.get_by_text("You may now close this window.")).to_be_visible()


@pytest.fixture
def pycloud_oauth2():
    client_id = os.environ.get("PCLOUD_OAUTH2_CLIENT_ID")
    client_secret = os.environ.get("PCLOUD_OAUTH2_CLIENT_SECRET")
    return PyCloud.oauth2_authorize(
        client_id, client_secret, tokenhandler=PlaywrightTokenHandler
    )


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
    fd = pycloud_oauth2.file_open(
        path=f"/{folder_for_tests}/upload.txt", flags=O_CREAT
    )["fd"]
    result = pycloud_oauth2.file_read(fd=fd, count=size)
    with open(testfile) as f:
        assert result == bytes(f.read(), "utf-8")
    result = pycloud_oauth2.file_close(fd=fd)
    assert result["result"] == 0


def test_listtokens(pycloud_oauth2):
    # listtokens endpoint is not available for OAuth authentication
    # see https://github.com/tomgross/pcloud/issues/61
    assert pycloud_oauth2.listtokens() == {"error": "Log in required.", "result": 1000}
