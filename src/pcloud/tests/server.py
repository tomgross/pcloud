#
from http.server import BaseHTTPRequestHandler
from multipart import MultipartParser
from multipart import parse_options_header
from os.path import dirname
from os.path import join
import socketserver


class MockHandler(BaseHTTPRequestHandler):
    # Handler for GET requests
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "applicaton/json")
        self.end_headers()
        # Send the json message
        path = self.path[1:].split("?")
        with open(join(dirname(__file__), "data", path[0] + ".json")) as f:
            data = f.read()
        self.wfile.write(bytes(data, "utf-8"))

    # Handler for POST requests
    def do_POST(self):
        content_length = int(self.headers["Content-Length"])
        _, options = parse_options_header(self.headers["Content-Type"])
        form = MultipartParser(
            self.rfile, options["boundary"], content_length=content_length
        )
        file_ = form.get("file")
        self.send_response(200)
        self.send_header("Content-type", "applicaton/json")
        self.end_headers()
        print(f"File: {file_.value.encode('utf-8')}, Size: {file_.size}", end="")
        # Send the json message
        self.wfile.write(
            bytes('{ "result": 0, "metadata": {"size": %s} }' % file_.size, "utf-8")
        )


class MockServer(socketserver.TCPServer):
    allow_reuse_address = True
