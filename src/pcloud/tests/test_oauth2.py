import os
import pytest

from pathlib import Path
from pcloud.api import PyCloud
from pcloud.api import O_CREAT
from pcloud.oauth2 import TokenHandler

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By


folder_for_tests = "integration-test"


class SeleniumTokenHandler(TokenHandler):
    """
    Class used to handle pClouds oAuth2 via selenium browser
    """

    def open_browser(self):
        ff_options = webdriver.FirefoxOptions()
        ff_options.headless = True
        self.driver = webdriver.Firefox(options=ff_options)
        self.driver.get(self.auth_url)
        login_input = self.driver.find_element(By.CLASS_NAME, "login-input-email")
        login_input.send_keys(os.environ.get("PCLOUD_USERNAME"))
        password_input = self.driver.find_element(By.CLASS_NAME, "login-input-password")
        password_input.send_keys(os.environ.get("PCLOUD_PASSWORD"))
        submit = self.driver.find_element(By.CLASS_NAME, "submitbut")
        submit.click()

    def close_browser(self):
        self.driver.quit()


@pytest.fixture
def pycloud_oauth2():
    client_id = os.environ.get("PCLOUD_OAUTH2_CLIENT_ID")
    client_secret = os.environ.get("PCLOUD_OAUTH2_CLIENT_SECRET")
    return PyCloud.oauth2_authorize(
        client_id, client_secret, tokenhandler=SeleniumTokenHandler
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
