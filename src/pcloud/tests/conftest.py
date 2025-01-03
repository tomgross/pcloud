import logging
import pytest

from pcloud.tests.server import MockHandler
from pcloud.tests.server import MockServer

from threading import Thread

log = logging.getLogger("pcloud")
log.setLevel(logging.INFO)

PORT = 5023


@pytest.fixture(scope="session")
def start_mock_server():
    """Start a mock server on port 5023"""
    httpd = MockServer(("", PORT), MockHandler)
    httpd_thread = Thread(target=httpd.serve_forever, daemon=True)
    log.info(f"Start mock server at port {PORT}")
    httpd_thread.start()
    yield start_mock_server
    log.info(f"Teardown mock server from port {PORT}")
    httpd.shutdown()
    httpd_thread.join()
