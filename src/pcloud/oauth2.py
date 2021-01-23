# -*- coding: utf-8 -*-
from http.server import BaseHTTPRequestHandler
from http.server import HTTPServer
from urllib.request import urlopen
from urllib.request import HTTPError
from urllib.parse import parse_qs
from urllib.parse import urlparse
from webbrowser import open_new


PORT = 65432
REDIRECT_URL = f"http://localhost:{PORT}/"


class HTTPServerHandler(BaseHTTPRequestHandler):
    """
    HTTP Server callbacks to handle pCloud OAuth2 redirects
    """

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        parsed_url = urlparse(self.path)
        query = parse_qs(parsed_url.query)
        code = query.get("code")
        if code:
            self.server.access_token = code[0]
            self.server.pc_hostname = query.get("hostname", "api.pcloud.com")[0]
            self.wfile.write(b"<html><h1>You may now close this window.</h1></html>")


class TokenHandler(object):
    """
    Class used to handle pClouds oAuth2
    """

    def __init__(self, client_id):
        self._id = client_id

    def get_access_token(self):
        open_new(
            f"https://my.pcloud.com/oauth2/authorize?response_type=code&redirect_uri={REDIRECT_URL}&client_id={self._id}"
        )
        httpServer = HTTPServer(("localhost", PORT), HTTPServerHandler)
        httpServer.handle_request()
        return httpServer.access_token, httpServer.pc_hostname
