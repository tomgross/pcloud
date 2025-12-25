from pcloud.api import PyCloud
from pcloud.utils import log
from pcloud.jsonprotocol import PCloudJSONConnection

import datetime
import json
import logging
import os
from hashlib import sha1

import aiofiles
import aiohttp

from pcloud.validate import MODE_AND, RequiredParameterCheck





default_settings = """
endpoint = "api"
token_expire = 31536000
oauth2 = false
"""

class AsyncPyCloud(PyCloud):

    @classmethod
    async def create(cls, username, password, settings):
        endpoint = settings["endpoint"]
        token_expire = settings["token_expire"]
        oauth2 = settings["oauth2"]

        self = cls()
        if  not endpoint in self.endpoints:
            log.error(
                f"Endpoint ({endpoint}) not found. Use one of: {', '.join(self.endpoints.keys())}"
            )
            return
        elif endpoint == "nearest":
            self.endpoint = await self.getnearestendpoint()
            conn = PCloudJSONConnection(self)
        else:
            protocol = self.endpoints.get(endpoint)
            self.endpoint = protocol.endpoint
            conn = protocol.connection(self)
        self.connection = conn.connect()

        log.info(f"Using pCloud API endpoint: {self.endpoint}")
        self.username = username.lower().encode("utf-8")
        self.password = password.encode("utf-8")
        self.token_expire = token_expire
        if oauth2:
            log.info("Using oauth2 authentication method.")
            self.access_token = password
            self.auth_token = ""
        elif not username and not password:
            log.info(
                "No username/password specified. Only public methods are available."
            )
            self.access_token = ""
            self.auth_token = ""
        else:
            log.info("Using username/password authentication method.")
            self.access_token = ""
            self.auth_token = await self.get_auth_token()

        return self

    async def getnearestendpoint(self):
        resp = await self._do_request(
            "getapiserver", authenticate=False, endpoint=self.default_api
        )
        return self._getendpointfromapiserverresp(resp)
    














    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.disconnect()

    async def connect(self):
        """Creates a session, must be called before any requests."""
        timeout = aiohttp.ClientTimeout(10)
        self.session = aiohttp.ClientSession(self.endpoint, headers=self.headers, timeout=timeout, raise_for_status=True)
        log.debug("Connected.")

    async def disconnect(self):
        if not self.session:
            return
        await self.session.close()
        log.debug("Disconnected.")
        self.session = None

    def change_token(self, new_token):
        self.token = new_token

    def _fix_path(self, path: str):
        if not path.startswith("/"):
            path = "/" + path
        if self.folder:
            path = f"/{self.folder}{path}"
        if path.endswith("/"):
            path = path[:-1]
        return path

    def _redact_auth(self, data: dict):
        # this is genius
        if 'auth' in data:
            data['auth'] = '***'
        return data

    def _prepare_params(self, params: dict = {}, auth=True, **kwargs):
        """Converts kwargs to params, and does auth check."""
        new_params = {**params, **kwargs}
        if not self.token and auth:
            raise NoTokenError
        if auth and not new_params.get('auth'):
            new_params['auth'] = self.token
        if new_params.get('path'):
            new_params['path'] = self._fix_path(new_params['path'])
        return new_params

    async def _do_request(self, url, auth=True, method="GET", data=None, params: dict = {}, **kwargs) -> dict:
        if not self.session:
            raise NoSessionError
        params = self._prepare_params(params, auth, **kwargs)
        log.debug(f"Request: {method} {url} {self._redact_auth(params.copy())}")
        async with self.session.request(method, url, data=data, params=params) as response:
            response_json = await response.json()
            log.debug(f"Response: {response_json} {response.status} {response.reason}")
            return response_json

    async def _get_text(self, url, auth=True, not_found_ok=False, params: dict = {}, **kwargs):
        if not self.session:
            raise NoSessionError
        params = self._prepare_params(params, auth, **kwargs)
        log.debug(f"Request: GET (text) {url} {self._redact_auth(params.copy())}")
        r = await self.session.get(url, params=params)
        log.debug(f"Response: {r.status} {r.reason}")
        text = await r.text()
        try:
            j = json.loads(text)
        except json.JSONDecodeError:
            return text
        if j.get("error"):
            log.debug(f"Bad response: {j}")
            if not_found_ok and "not found" in j["error"]:
                return
            raise Exception(j["error"])
        return text

    async def _default_get(self, url, **kwargs):
        if not self.session:
            raise NoSessionError
        r = await self.session.get(url, **kwargs)
        return await r.read()

    # Authentication stuff
    async def getdigest(self):
        resp = await self._do_request("getdigest", False)
        return bytes(resp["digest"], "utf-8")

    async def get_auth(self, email: str, password: str, token_expire=31536000, verbose=False) -> str:
        """Logs into pCloud and returns the token. Defaults to 1 year. Also prints it if verbose."""
        digest = await self.getdigest()
        passworddigest = sha1(password.encode("utf-8") + bytes(sha1(email.encode("utf-8")).hexdigest(), "utf-8") + digest)
        params = {
            "getauth": 1,
            "username": email,
            "digest": digest.decode("utf-8"),
            "passworddigest": passworddigest.hexdigest(),
            "authexpire": token_expire
        }
        response = await self.userinfo(auth=False, params=params)
        token = response['auth']
        if verbose:
            print(token)
        return token

    # General
    async def userinfo(self, **kwargs):
        return await self._do_request("userinfo", **kwargs)

    def supportedlanguages(self):
        return self._do_request("supportedlanguages")

    @RequiredParameterCheck(("language",))
    async def setlanguage(self, **kwargs):
        return await self._do_request("setlanguage", **kwargs)

    @RequiredParameterCheck(("mail", "reason", "message"), mode=MODE_AND)
    async def feedback(self, **kwargs):
        return await self._do_request("feedback", **kwargs)

    async def currentserver(self):
        return await self._do_request("currentserver")

    async def diff(self, **kwargs):
        return await self._do_request("diff", **kwargs)

    async def getfilehistory(self, **kwargs):
        return await self._do_request("getfilehistory", **kwargs)

    async def getip(self):
        return await self._do_request("getip")

    async def getapiserver(self):
        return await self._do_request("getapiserver")

    # Folder
    @RequiredParameterCheck(("path", "folderid", "name"))
    async def createfolder(self, **kwargs):
        return await self._do_request("createfolder", **kwargs)

    @RequiredParameterCheck(("path", "folderid", "name"))
    async def createfolderifnotexists(self, **kwargs):
        return await self._do_request("createfolderifnotexists", **kwargs)

    @RequiredParameterCheck(("path", "folderid"))
    async def listfolder(self, **kwargs):
        return await self._do_request("listfolder", **kwargs)

    @RequiredParameterCheck(("path", "folderid"))
    async def renamefolder(self, **kwargs):
        return await self._do_request("renamefolder", **kwargs)

    @RequiredParameterCheck(("path", "folderid"))
    async def deletefolder(self, **kwargs):
        return await self._do_request("deletefolder", **kwargs)

    @RequiredParameterCheck(("path", "folderid"))
    async def deletefolderrecursive(self, **kwargs):
        return await self._do_request("deletefolderrecursive", **kwargs)

    @RequiredParameterCheck(("path", "folderid"))
    @RequiredParameterCheck(("topath", "tofolderid"))
    async def copyfolder(self, **kwargs):
        return await self._do_request("copyfolder", **kwargs)

    # File
    @RequiredParameterCheck(("files", "data"))
    async def uploadfile(self, **kwargs):
        # TODO: upload chunks (streaming)
        data = kwargs.get("data")
        if data:
            if isinstance(data, aiohttp.FormData):
                return await self._do_request("uploadfile", method="POST", **kwargs)
            else:
                raise ValueError("data must be aiohttp.FormData")
        files = kwargs.pop("files", [])
        if not files:
            raise ValueError("no data or files provided")
        if not isinstance(files, list):
            raise TypeError("files must be a list of file paths")
        log.debug(f"Uploading {len(files)} files: {files}")
        form = aiohttp.FormData()
        for file_path in files:
            if not os.path.isfile(file_path):
                raise FileNotFoundError(f"File does not exist: {file_path}")
            filename = os.path.basename(file_path)
            async with aiofiles.open(file_path, mode="rb") as f:
                content = await f.read()
            form.add_field("file", content, filename=filename)
        kwargs["data"] = form
        return await self._do_request("uploadfile", method="POST", **kwargs)

    @RequiredParameterCheck(("path", "folderid"))
    async def upload_one_file(self, filename: str, content, **kwargs):
        if not isinstance(content, bytes) and not isinstance(content, str):
            raise TypeError("content must be bytes or str")
        data = aiohttp.FormData()
        data.add_field('filename', content, filename=filename)
        return await self.uploadfile(data=data, **kwargs)

    @RequiredParameterCheck(("progresshash",))
    async def uploadprogress(self, **kwargs):
        return await self._do_request("uploadprogress", **kwargs)

    @RequiredParameterCheck(("url",))
    async def downloadfile(self, **kwargs):
        return await self._do_request("downloadfile", **kwargs)

    @RequiredParameterCheck(("url",))
    async def downloadfileasync(self, **kwargs):
        return await self._do_request("downloadfileasync", **kwargs)

    @RequiredParameterCheck(("path", "fileid"))
    async def copyfile(self, **kwargs):
        return await self._do_request("copyfile", **kwargs)

    @RequiredParameterCheck(("path", "fileid"))
    async def checksumfile(self, **kwargs):
        return await self._do_request("checksumfile", **kwargs)

    @RequiredParameterCheck(("path", "fileid"))
    async def deletefile(self, **kwargs):
        return await self._do_request("deletefile", **kwargs)

    async def renamefile(self, **kwargs):
        return await self._do_request("renamefile", **kwargs)

    @RequiredParameterCheck(("path", "fileid"))
    async def stat(self, **kwargs):
        return await self._do_request("stat", **kwargs)

    async def search(self, query: str, **kwargs):
        """Undocumented, also supports offset and limit kwargs."""
        return await self._do_request('search', params={'query': query, **kwargs})

    # Auth
    async def sendverificationemail(self, **kwargs):
        return await self._do_request("sendverificationemail", **kwargs)

    async def verifyemail(self, **kwargs):
        return await self._do_request("verifyemail", **kwargs)

    async def changepassword(self, **kwargs):
        return await self._do_request("changepassword", **kwargs)

    async def lostpassword(self, **kwargs):
        return await self._do_request("lostpassword", **kwargs)

    async def resetpassword(self, **kwargs):
        return await self._do_request("resetpassword", **kwargs)

    async def register(self, **kwargs):
        return await self._do_request("register", **kwargs)

    async def invite(self, **kwargs):
        return await self._do_request("invite", **kwargs)

    async def userinvites(self, **kwargs):
        return await self._do_request("userinvites", **kwargs)

    async def logout(self, **kwargs):
        return await self._do_request("logout", **kwargs)

    async def listtokens(self, **kwargs):
        return await self._do_request("listtokens", **kwargs)

    async def deletetoken(self, **kwargs):
        return await self._do_request("deletetoken", **kwargs)

    async def sendchangemail(self, **kwargs):
        return await self._do_request("sendchangemail", **kwargs)

    async def changemail(self, **kwargs):
        return await self._do_request("changemail", **kwargs)

    async def senddeactivatemail(self, **kwargs):
        return await self._do_request("senddeactivatemail", **kwargs)

    async def deactivateuser(self, **kwargs):
        return await self._do_request("deactivateuser", **kwargs)

    # Streaming
    def _make_link(self, response: dict, not_found_ok=False):
        if 'not found' in response.get('error', ''):
            if not_found_ok:
                return
            raise Exception(response['error'])
        return f"https://{response['hosts'][0]}{response['path']}"

    @RequiredParameterCheck(("path", "fileid"))
    async def getfilelink(self, not_found_ok=False, **kwargs):
        """Returns a link to the file."""
        response = await self._do_request("getfilelink", **kwargs)
        return self._make_link(response, not_found_ok)

    @RequiredParameterCheck(("path", "fileid"))
    async def download_file(self, not_found_ok=False, **kwargs):
        download_url = await self.getfilelink(not_found_ok, **kwargs)
        if download_url is None:
            return
        return await self._default_get(download_url)

    @RequiredParameterCheck(("path", "fileid"))
    async def getvideolink(self, **kwargs):
        response = await self._do_request("getvideolink", **kwargs)
        return self._make_link(response)

    @RequiredParameterCheck(("path", "fileid"))
    async def getvideolinks(self, **kwargs):
        return await self._do_request("getvideolinks", **kwargs)

    @RequiredParameterCheck(("path", "fileid"))
    async def getaudiolink(self, **kwargs):
        response = await self._do_request("getaudiolink", **kwargs)
        return self._make_link(response)

    @RequiredParameterCheck(("path", "fileid"))
    async def gethlslink(self, **kwargs):
        response = await self._do_request("gethlslink", **kwargs)
        return self._make_link(response)

    @RequiredParameterCheck(("path", "fileid"))
    async def gettextfile(self, not_found_ok=False, **kwargs):
        return await self._get_text("gettextfile", not_found_ok=not_found_ok, **kwargs)

    # Archiving
    @RequiredParameterCheck(("folderid", "folderids", "fileids"))
    async def getzip(self, **kwargs):
        return await self._do_request("getzip", json=False, **kwargs)

    @RequiredParameterCheck(("folderid", "folderids", "fileids"))
    async def getziplink(self, **kwargs):
        return await self._do_request("getziplink", **kwargs)

    @RequiredParameterCheck(("folderid", "folderids", "fileids"))
    @RequiredParameterCheck(("topath", "tofolderid", "toname"))
    async def savezip(self, **kwargs):
        return await self._do_request("savezip", **kwargs)

    @RequiredParameterCheck(("path", "fileid"))
    @RequiredParameterCheck(("topath", "tofolderid"))
    async def extractarchive(self, **kwargs):
        return await self._do_request("extractarchive", **kwargs)

    @RequiredParameterCheck(("progresshash",))
    async def extractarchiveprogress(self, **kwargs):
        return await self._do_request("extractarchiveprogress", **kwargs)

    @RequiredParameterCheck(("progresshash",))
    async def savezipprogress(self, **kwargs):
        return await self._do_request("savezipprogress", **kwargs)

    # Sharing
    @RequiredParameterCheck(("path", "folderid"))
    @RequiredParameterCheck(("mail", "permissions"), mode=MODE_AND)
    async def sharefolder(self, **kwargs):
        return await self._do_request("sharefolder", **kwargs)

    async def listshares(self, **kwargs):
        return await self._do_request("listshares", **kwargs)

    # Public links
    @RequiredParameterCheck(("path", "fileid"))
    async def getfilepublink(self, **kwargs):
        return await self._do_request("getfilepublink", **kwargs)

    @RequiredParameterCheck(("code", "fileid"))
    async def getpublinkdownload(self, **kwargs):
        return await self._do_request("getpublinkdownload", **kwargs)

    @RequiredParameterCheck(("path", "folderid"))
    async def gettreepublink(self, **kwargs):
        raise NotImplementedError

    @RequiredParameterCheck(("code",))
    async def showpublink(self, **kwargs):
        return await self._do_request("showpublink", auth=False, **kwargs)

    @RequiredParameterCheck(("code",))
    async def copypubfile(self, **kwargs):
        return await self._do_request("copypubfile", **kwargs)

    async def listpublinks(self, **kwargs):
        return await self._do_request("listpublinks", **kwargs)

    async def listplshort(self, **kwargs):
        return await self._do_request("listplshort", **kwargs)

    @RequiredParameterCheck(("linkid",))
    async def deletepublink(self, **kwargs):
        return await self._do_request("deletepublink", **kwargs)

    @RequiredParameterCheck(("linkid",))
    async def changepublink(self, **kwargs):
        return await self._do_request("changepublink", **kwargs)

    @RequiredParameterCheck(("path", "folderid"))
    async def getfolderpublink(self, **kwargs):
        expire = kwargs.get("expire")
        if expire is not None:
            kwargs["expire"] = to_api_datetime(expire)
        return await self._do_request("getfolderpublink", **kwargs)

    @RequiredParameterCheck(("code",))
    async def getpubzip(self, unzip=False, **kwargs):
        raise NotImplementedError
        # TODO: Implement this in async
        # zipresponse = self._do_request(
        #     "getpubzip", auth=False, json=False, **kwargs
        # )
        # if not unzip:
        #     return zipresponse
        # zipfmem = BytesIO(zipresponse)
        # code = kwargs.get("code")
        # try:
        #     zf = zipfile.ZipFile(zipfmem)
        # except zipfile.BadZipfile:
        #     # Could also be the case, if public link is password protected.
        #     log.warn(
        #         f"No valid zipfile found for code f{code}. Empty content is returned."
        #     )
        #     return ""
        # names = zf.namelist()
        # if names:
        #     contents = zf.read(names[0])
        # else:
        #     log.warn(f"Zip file is empty for code f{code}. Empty content is returned.")
        #     contents = ""
        # return contents

    # Trash
    async def trash_list(self, **kwargs):
        return await self._do_request("trash_list", **kwargs)

    @RequiredParameterCheck(("fileid", "folderid"))
    async def trash_restorepath(self, **kwargs):
        return await self._do_request("trash_restorepath", **kwargs)

    @RequiredParameterCheck(("fileid", "folderid"))
    async def trash_restore(self, **kwargs):
        return await self._do_request("trash_restore", **kwargs)

    @RequiredParameterCheck(("fileid", "folderid"))
    async def trash_clear(self, **kwargs):
        return await self._do_request("trash_clear", **kwargs)