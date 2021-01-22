from pcloud.tests.server import MockHandler
from pcloud.tests.server import MockServer
import pytest
from threading import Thread

PORT = 5000


@pytest.fixture(scope="session")
def start_mock_server():
    """Start a mock server on port 5000"""
    httpd = MockServer(("", PORT), MockHandler)
    httpd_thread = Thread(target=httpd.serve_forever, daemon=True)
    httpd_thread.start()
    print("start")
    yield start_mock_server
    print("teardown")
    httpd.shutdown()
    httpd_thread.join()
