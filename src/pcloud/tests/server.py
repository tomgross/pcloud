#
from http.server import BaseHTTPRequestHandler

from os.path import dirname
from os.path import join
import socketserver


class MockHandler(BaseHTTPRequestHandler):
    # Handler for the GET requests
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'applicaton/json')
        self.end_headers()
        # Send the json message
        path = self.path[1:].split('?')
        with open(join(dirname(
                __file__), 'data', path[0] + '.json')) as f:
            data = f.read()
        self.wfile.write(bytes(data, 'utf-8'))


class MockServer(socketserver.TCPServer):
    allow_reuse_address = True
