from pcloud.tests.server import MockHandler
from pcloud.tests.server import MockServer
import pytest
from threading import Thread

PORT = 5000


@pytest.fixture(scope="session")
def start_mock_server():
    """ Start a mock server on port 5000
    """
    httpd = MockServer(("", PORT), MockHandler)
    httpd_thread = Thread(target=httpd.serve_forever)
    httpd_thread.setDaemon(False)
    httpd_thread.start()
    yield start_mock_server
    httpd_thread._is_stopped = True
    httpd_thread._tstate_lock = None
    httpd_thread._stop()
