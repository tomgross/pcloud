import requests

from pcloud.utils import log
from requests_toolbelt.multipart.encoder import MultipartEncoder
from pcloud.jsonprotocol import PCloudJSONConnection

class NoOpSession(object):
    kwargs = {}

    def get(self, url, **kwargs):
        self.kwargs = kwargs
        self.kwargs["url"] = url
        return self

    def json(self):
        return self.kwargs

class PCloudDummyConnection(PCloudJSONConnection):
    """Connection to pcloud.com based on their JSON protocol."""

    allowed_endpoints = frozenset(["test"])

    def __init__(self, api):
        """Connect to pcloud API based on their JSON protocol."""
        self.session = NoOpSession()
        self.api = api

    def connect(self):
        return self
    
    def do_get_request(self, method, authenticate=True, json=True, endpoint=None, **kw):
        if "noop" in kw:
            kw.pop("noop")
            params = {
                "params": kw,
                "url": self.api.endpoint + method
            }
            return params
        else:
            return super().do_get_request(method, authenticate, json, endpoint, **kw)

    def upload(self, method, files, **kwargs):
        if self.api.auth_token:  # Password authentication
            kwargs["auth"] = self.api.auth_token
        elif self.api.access_token:  # OAuth2 authentication
            kwargs["access_token"] = self.api.access_token
        fields = list(kwargs.items())
        fields.extend(files)

        # from requests import Request, Session

        # s = Session()

        # for entry in files:
        #     filename, fd = entry[1]
        #     fields["filename"] = filename
        #     req = Request('PUT', self.api.endpoint + method, data=fields)
        #     prepped = req.prepare()
        #     prepped.body = fd
        #     resp = s.send(prepped)

        # resp = self.session.post(self.api.endpoint + method, files=files, data=kwargs)
        m = MultipartEncoder(fields=fields)
        resp = requests.post(
            self.api.endpoint + method, data=m, headers={"Content-Type": m.content_type}
        )
        # data = dump_all(resp)
        # print(data.decode('utf-8'))
        return resp.json()
