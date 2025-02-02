import httpx

from pcloud.utils import log


class PCloudJSONConnection(object):
    """Connection to pcloud.com based on their JSON protocol."""

    allowed_endpoints = frozenset(["api", "eapi", "nearest"])

    def __init__(self, api):
        """Connect to pcloud API based on their JSON protocol."""
        self.session = httpx.Client()
        self.api = api

    def connect(self):
        return self

    def do_get_request(self, method, authenticate=True, json=True, endpoint=None, **kw):
        if authenticate and self.api.auth_token:  # Password authentication
            params = {"auth": self.api.auth_token}
        elif authenticate and self.api.access_token:  # OAuth2 authentication
            params = {"access_token": self.api.access_token}
        else:
            params = {}
        if endpoint is None:
            endpoint = self.api.endpoint
        params.update(kw)
        log.debug("Doing request to %s%s", endpoint, method)
        log.debug("Params: %s", params)
        if "use_session" in kw:
            get_method = self.session.get
        else:
            get_method = httpx.get
        resp = get_method(endpoint + method, params=params)
        resp.raise_for_status()
        if json:
            result = resp.json()
        else:
            result = resp.content
        log.debug("Response: %s", result)
        return result

    def upload(self, method, files, **kwargs):
        if self.api.auth_token:  # Password authentication
            kwargs["auth"] = self.api.auth_token
        elif self.api.access_token:  # OAuth2 authentication
            kwargs["access_token"] = self.api.access_token
        log.debug(f"Upload files: {files}")
        log.debug(f"Upload fields: {kwargs}")
        resp = httpx.post(self.api.endpoint + method, data=kwargs, files=files)
        return resp.json()
