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

    def do_get_request(self, method, authenticate=True, json=True, endpoint=None, **kw):
        if "noop" in kw:
            kw.pop("noop")
            params = {"params": kw, "url": self.api.endpoint + method}
            return params
        else:
            return super().do_get_request(method, authenticate, json, endpoint, **kw)
