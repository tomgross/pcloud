import requests

from pcloud.utils import log
from requests_toolbelt.multipart.encoder import MultipartEncoder


class PCloudJSONConnection(object):
    """Connection to pcloud.com based on their JSON protocol."""

    allowed_endpoints = frozenset(["api", "eapi", "nearest"])

    def __init__(self, api):
        """Connect to pcloud API based on their JSON protocol."""
        self.session = requests.Session()
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
            get_method = requests.get
        resp = get_method(endpoint + method, params=params, allow_redirects=False)
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
        fields = list(kwargs.items())
        fields.extend(files)
        m = MultipartEncoder(fields=fields)
        resp = requests.post(
            self.api.endpoint + method, data=m, headers={"Content-Type": m.content_type}
        )
        return resp.json()
