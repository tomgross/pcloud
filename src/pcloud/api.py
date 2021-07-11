from hashlib import sha1
from io import BytesIO
from pcloud.oauth2 import TokenHandler
from pcloud.validate import RequiredParameterCheck
from urllib.parse import urlparse
from urllib.parse import urlunsplit

import argparse
import logging
import requests
import sys


log = logging.getLogger("pycloud")
log.setLevel(logging.INFO)

handler = logging.StreamHandler(sys.stderr)
handler.setLevel(logging.INFO)
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)
log.addHandler(handler)

# File open flags https://docs.pcloud.com/methods/fileops/file_open.html
O_WRITE = int("0x0002", 16)
O_CREAT = int("0x0040", 16)
O_EXCL = int("0x0080", 16)
O_TRUNC = int("0x0200", 16)
O_APPEND = int("0x0400", 16)

ONLY_PCLOUD_MSG = "This method can't be used from web applications. Referrer is restricted to pcloud.com."


# Exceptions
class AuthenticationError(Exception):
    """ Authentication failed """


class OnlyPcloudError(NotImplementedError):
    """ Feature restricted to pCloud """


def main():
    parser = argparse.ArgumentParser(description="pCloud command line client")
    parser.add_argument(
        "username", help="The username for login into your pCloud account"
    )
    parser.add_argument(
        "password", help="The password for login into your pCloud account"
    )
    args = parser.parse_args()
    pyc = PyCloud(args.username, args.password)
    print(pyc)


class PyCloud(object):

    endpoints = {
        "api": "https://api.pcloud.com/",
        "eapi": "https://eapi.pcloud.com/",
        "test": "http://localhost:5000/",
        "nearest": "",
    }

    def __init__(
        self, username, password, endpoint="api", token_expire=31536000, oauth2=False
    ):
        self.session = requests.Session()
        if endpoint not in self.endpoints:
            log.error(
                "Endpoint (%s) not found. Use one of: %s",
                endpoint,
                ",".join(self.endpoints.keys()),
            )
            return
        elif endpoint == "nearest":
            self.endpoint = self.getnearestendpoint()
        else:
            self.endpoint = self.endpoints.get(endpoint)
        log.info(f"Using pCloud API endpoint: {self.endpoint}")
        self.username = username.lower().encode("utf-8")
        self.password = password.encode("utf-8")
        self.token_expire = token_expire
        if oauth2:
            self.access_token = password
            self.auth_token = ""
        else:
            self.access_token = ""
            self.auth_token = self.get_auth_token()

    @classmethod
    def oauth2_authorize(
        cls,
        client_id,
        client_secret,
        token_expire=31536000,
    ):
        ep = {urlparse(y).netloc: x for x, y in PyCloud.endpoints.items()}
        code, hostname = TokenHandler(client_id).get_access_token()
        params = {"client_id": client_id, "client_secret": client_secret, "code": code}
        endpoint = ep.get(hostname)
        endpoint_url = PyCloud.endpoints.get(endpoint)
        resp = requests.get(endpoint_url + "oauth2_token", params=params).json()
        access_token = resp.get("access_token")
        return cls("", access_token, endpoint, token_expire, oauth2=True)

    def _do_request(self, method, authenticate=True, json=True, endpoint=None, **kw):
        if authenticate and self.auth_token:  # Password authentication
            params = {"auth": self.auth_token}
        elif authenticate and self.access_token:  # OAuth2 authentication
            params = {"access_token": self.access_token}
        else:
            params = {}
        if endpoint is None:
            endpoint = self.endpoint
        params.update(kw)
        log.debug("Doing request to %s%s", endpoint, method)
        log.debug("Params: %s", params)
        resp = self.session.get(endpoint + method, params=params)
        if json:
            resp = resp.json()
        else:
            resp = resp.content
        log.debug("Response: %s", resp)
        return resp

    # Authentication
    def getdigest(self):
        resp = self._do_request("getdigest", authenticate=False)
        return bytes(resp["digest"], "utf-8")

    def get_auth_token(self):
        digest = self.getdigest()
        passworddigest = sha1(
            self.password + bytes(sha1(self.username).hexdigest(), "utf-8") + digest
        )
        params = {
            "getauth": 1,
            "logout": 1,
            "username": self.username.decode("utf-8"),
            "digest": digest.decode("utf-8"),
            "passworddigest": passworddigest.hexdigest(),
            "authexpire": self.token_expire,
        }
        resp = self._do_request("userinfo", authenticate=False, **params)
        if "auth" not in resp:
            raise AuthenticationError(resp)
        return resp["auth"]

    # General
    def userinfo(self, **kwargs):
        return self._do_request("userinfo")

    def supportedlanguages(self, **kwargs):
        return self._do_request("supportedlanguages")

    def getnearestendpoint(self):
        default_api = self.endpoints.get("api")
        resp = self._do_request(
            "getapiserver", authenticate=False, endpoint=default_api
        )
        api = resp.get("api")
        if len(api):
            return urlunsplit(["https", api[0], "/", "", ""])
        else:
            return default_api

    @RequiredParameterCheck(("language",))
    def setlanguage(self):
        raise NotImplementedError

    def feedback(self):
        raise NotImplementedError

    def currentserver(self):
        return self._do_request("currentserver")

    def diff(self):
        raise NotImplementedError

    def getfilehistory(self):
        raise NotImplementedError

    def getip(self):
        return self._do_request("getip")

    def getapiserver(self):
        return self._do_request("getapiserver")

    # Folders
    @RequiredParameterCheck(("path", "folderid", "name"))
    def createfolder(self, **kwargs):
        return self._do_request("createfolder", **kwargs)

    @RequiredParameterCheck(("path", "folderid", "name"))
    def createfolderifnotexists(self, **kwargs):
        return self._do_request("createfolderifnotexists", **kwargs)

    @RequiredParameterCheck(("path", "folderid"))
    def listfolder(self, **kwargs):
        return self._do_request("listfolder", **kwargs)

    @RequiredParameterCheck(("path", "folderid"))
    def renamefolder(self, **kwargs):
        return self._do_request("renamefolder", **kwargs)

    @RequiredParameterCheck(("path", "folderid"))
    def deletefolder(self, **kwargs):
        return self._do_request("deletefolder", **kwargs)

    @RequiredParameterCheck(("path", "folderid"))
    def deletefolderrecursive(self, **kwargs):
        return self._do_request("deletefolderrecursive", **kwargs)

    def copyfolder(self, **kwargs):
        raise NotImplementedError

    # File
    def _upload(self, method, files, **kwargs):
        kwargs["auth"] = self.auth_token
        resp = self.session.post(self.endpoint + method, files=files, data=kwargs)
        return resp.json()

    @RequiredParameterCheck(("files", "data"))
    def uploadfile(self, **kwargs):
        """upload a file to pCloud

        1) You can specify a list of filenames to read
        files=['/home/pcloud/foo.txt', '/home/pcloud/bar.txt']

        2) you can specify binary data via the data parameter and
        need to specify the filename too
        data='Hello pCloud', filename='foo.txt'
        """
        if "files" in kwargs:
            upload_files = kwargs.pop("files", [])
            files = [("file", open(f, "rb")) for f in upload_files]
        else:  # 'data' in kwargs:
            files = {
                "f": (kwargs.pop("filename", "data-upload.bin"), kwargs.pop("data"))
            }
        return self._upload("uploadfile", files, **kwargs)

    @RequiredParameterCheck(("progresshash",))
    def uploadprogress(self, **kwargs):
        return self._do_request("uploadprogress", **kwargs)

    @RequiredParameterCheck(("url",))
    def downloadfile(self, **kwargs):
        return self._do_request("downloadfile", **kwargs)

    def copyfile(self, **kwargs):
        raise NotImplementedError

    @RequiredParameterCheck(("path", "fileid"))
    def checksumfile(self, **kwargs):
        return self._do_request("checksumfile", **kwargs)

    @RequiredParameterCheck(("path", "fileid"))
    def deletefile(self, **kwargs):
        return self._do_request("deletefile", **kwargs)

    def renamefile(self, **kwargs):
        return self._do_request("renamefile", **kwargs)

    @RequiredParameterCheck(("path", "fileid"))
    def stat(self, **kwargs):
        return self._do_request("stat", **kwargs)

    # Auth API methods
    def sendverificationemail(self, **kwargs):
        return self._do_request("sendverificationemail", **kwargs)

    def verifyemail(self, **kwargs):
        return self._do_request("verifyemail", **kwargs)

    def changepassword(self, **kwargs):
        return self._do_request("changepassword", **kwargs)

    def lostpassword(self, **kwargs):
        return self._do_request("lostpassword", **kwargs)

    def resetpassword(self, **kwargs):
        return self._do_request("resetpassword", **kwargs)

    def register(self, **kwargs):
        return self._do_request("register", **kwargs)

    def invite(self, **kwargs):
        return self._do_request("invite", **kwargs)

    def userinvites(self, **kwargs):
        return self._do_request("userinvites", **kwargs)

    def logout(self, **kwargs):
        return self._do_request("logout", **kwargs)

    def listtokens(self, **kwargs):
        return self._do_request("listtokens", **kwargs)

    def deletetoken(self, **kwargs):
        return self._do_request("deletetoken", **kwargs)

    # Streaming
    def getfilelink(self, **kwargs):
        raise OnlyPcloudError(ONLY_PCLOUD_MSG)

    def getvideolink(self, **kwargs):
        raise OnlyPcloudError(ONLY_PCLOUD_MSG)

    def getvideolinks(self, **kwargs):
        raise OnlyPcloudError(ONLY_PCLOUD_MSG)

    def getaudiolink(self, **kwargs):
        raise OnlyPcloudError(ONLY_PCLOUD_MSG)

    def gethlslink(self, **kwargs):
        raise OnlyPcloudError(ONLY_PCLOUD_MSG)

    def gettextfile(self, **kwargs):
        raise OnlyPcloudError(ONLY_PCLOUD_MSG)

    # File API methods
    @RequiredParameterCheck(("flags",))
    def file_open(self, **kwargs):
        return self._do_request("file_open", **kwargs)

    @RequiredParameterCheck(("fd",))
    def file_read(self, **kwargs):
        return self._do_request("file_read", json=False, **kwargs)

    @RequiredParameterCheck(("fd",))
    def file_pread(self, **kwargs):
        return self._do_request("file_pread", json=False, **kwargs)

    @RequiredParameterCheck(("fd", "data"))
    def file_pread_ifmod(self, **kwargs):
        return self._do_request("file_pread_ifmod", json=False, **kwargs)

    @RequiredParameterCheck(("fd",))
    def file_size(self, **kwargs):
        return self._do_request("file_size", **kwargs)

    @RequiredParameterCheck(("fd",))
    def file_truncate(self, **kwargs):
        return self._do_request("file_truncate", **kwargs)

    @RequiredParameterCheck(("fd", "data"))
    def file_write(self, **kwargs):
        files = {"file": ("upload-file.io", BytesIO(kwargs.pop("data")))}
        return self._upload("file_write", files, **kwargs)

    @RequiredParameterCheck(("fd",))
    def file_pwrite(self, **kwargs):
        return self._do_request("file_pwrite", **kwargs)

    @RequiredParameterCheck(("fd",))
    def file_checksum(self, **kwargs):
        return self._do_request("file_checksum", **kwargs)

    @RequiredParameterCheck(("fd",))
    def file_seek(self, **kwargs):
        return self._do_request("file_seek", **kwargs)

    @RequiredParameterCheck(("fd",))
    def file_close(self, **kwargs):
        return self._do_request("file_close", **kwargs)

    @RequiredParameterCheck(("fd",))
    def file_lock(self, **kwargs):
        return self._do_request("file_lock", **kwargs)

    # Archiving
    @RequiredParameterCheck(("path", "fileid"))
    @RequiredParameterCheck(("topath", "tofolderid"))
    def extractarchive(self, **kwargs):
        return self._do_request("extractarchive", **kwargs)

    @RequiredParameterCheck(("folderid", "folderids", "fileids"))
    def getzip(self, **kwargs):
        return self._do_request("getzip", json=False, **kwargs)

    @RequiredParameterCheck(("folderid", "folderids", "fileids"))
    def getziplink(self, **kwargs):
        return self._do_request("getziplink", **kwargs)

    @RequiredParameterCheck(("folderid", "folderids", "fileids"))
    @RequiredParameterCheck(("topath", "tofolderid", "toname"))
    def savezip(self, **kwargs):
        return self._do_request("savezip", **kwargs)

    @RequiredParameterCheck(("progresshash",))
    def extractarchiveprogress(self, **kwargs):
        return self._do_request("extractarchiveprogress", **kwargs)

    @RequiredParameterCheck(("progresshash",))
    def savezipprogress(self, **kwargs):
        return self._do_request("savezipprogress", **kwargs)

    # Sharing
    def sharefolder(self, **kwargs):
        raise NotImplementedError

    def listshares(self, **kwargs):
        return self._do_request("listshares")

    # Trash methods
    def trash_list(self, **kwargs):
        return self._do_request("trash_list", **kwargs)

    @RequiredParameterCheck(("fileid", "folderid"))
    def trash_clear(self, **kwargs):
        return self._do_request("trash_clear", **kwargs)

    def trash_restorepath(self, **kwargs):
        raise NotImplementedError

    @RequiredParameterCheck(("fileid", "folderid"))
    def trash_restore(self, **kwargs):
        raise NotImplementedError


if __name__ == "__main__":
    main()
