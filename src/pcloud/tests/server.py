#
from http.server import BaseHTTPRequestHandler

from os.path import dirname
from os.path import join
import socketserver
import cgi


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
        form = cgi.FieldStorage(
            fp=self.rfile,
            headers=self.headers,
            environ={
                "REQUEST_METHOD": "POST",
                "CONTENT_TYPE": self.headers["Content-Type"],
            },
        )
        if "upload.txt" in form:
            file_ = form.getvalue("upload.txt")
        else:
            file_ = form.getvalue("file")
        size = len(file_)
        self.send_response(200)
        self.send_header("Content-type", "applicaton/json")
        self.end_headers()
        print(f"File: {file_}, Size: {size}", end="")
        # Send the json message
        self.wfile.write(
            bytes('{ "result": 0, "metadata": {"size": %s} }' % size, "utf-8")
        )


class MockServer(socketserver.TCPServer):
    allow_reuse_address = True
