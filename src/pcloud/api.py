import io
import os
import httpx
import zipfile

from hashlib import sha1
from io import BytesIO

from pcloud.protocols import JsonAPIProtocol
from pcloud.protocols import JsonEAPIProtocol
from pcloud.protocols import BinAPIProtocol
from pcloud.protocols import BinEAPIProtocol
from pcloud.protocols import TestProtocol
from pcloud.protocols import NearestProtocol
from pcloud.jsonprotocol import PCloudJSONConnection
from pcloud.oauth2 import TokenHandler
from pcloud.utils import log
from pcloud.utils import to_api_datetime
from pcloud.validate import MODE_AND
from pcloud.validate import RequiredParameterCheck

from urllib.parse import urlparse
from urllib.parse import urlunsplit

# Crypto is optional; import defensively so missing helpers don't disable all crypto
try:
    import pcloud.crypto as _pcrypto
    decrypt_private_key = getattr(_pcrypto, "decrypt_private_key", None)
    KeyPair = getattr(_pcrypto, "KeyPair", None)
    decrypt_filename = getattr(_pcrypto, "decrypt_filename", None)
    decrypt_file_contents = getattr(_pcrypto, "decrypt_file_contents", None)
    CRYPTO_AVAILABLE = decrypt_private_key is not None and KeyPair is not None
except ImportError:
    CRYPTO_AVAILABLE = False
    KeyPair = None
    decrypt_private_key = None
    decrypt_filename = None
    decrypt_file_contents = None


ONLY_PCLOUD_MSG = "This method can't be used from web applications. Referrer is restricted to pcloud.com."


# Exceptions
class AuthenticationError(Exception):
    """Authentication failed"""


class OnlyPcloudError(NotImplementedError):
    """Feature restricted to pCloud"""


class InvalidFileModeError(Exception):
    """File mode not supported"""


class PyCloud(object):
    endpoints = {
        "api": JsonAPIProtocol,
        "eapi": JsonEAPIProtocol,
        "test": TestProtocol,
        "binapi": BinAPIProtocol,
        "bineapi": BinEAPIProtocol,
        "nearest": NearestProtocol,
    }

    def __init__(
        self, username, password, endpoint="api", token_expire=31536000, oauth2=False, crypto_password=None
    ):
        if endpoint not in self.endpoints:
            log.error(
                f"Endpoint ({endpoint}) not found. Use one of: {', '.join(self.endpoints.keys())}"
            )
            return
        elif endpoint == "nearest":
            self.endpoint = self.getnearestendpoint()
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
        self.crypto_password = crypto_password
        self.keypair = None
        self._folder_key_cache = {}
        self._file_key_cache = {}
        
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
            self.auth_token = self.get_auth_token()
        
        # Initialize crypto keys if crypto_password is provided
        if self.crypto_password:
            if not CRYPTO_AVAILABLE:
                log.error(
                    "Crypto password provided but crypto backend is unavailable. "
                    "Ensure pycryptodome is installed and pcloud.crypto exposes decrypt_private_key. "
                    "Try: pip install 'pcloud[crypto]'"
                )
            else:
                try:
                    self._init_crypto_keys()
                except Exception as e:
                    log.error(f"Failed to initialize crypto keys: {e}")

    @classmethod
    def oauth2_authorize(
        cls, client_id, client_secret, token_expire=31536000, tokenhandler=TokenHandler
    ):
        """OAuth2.0 authorization flow
        See https://docs.pcloud.com/methods/oauth_2.0/authorize.html

        Per default the Python webbrowser library, which opens
        a real browser used for URL redirection.
        You can provide your own token handler
        (i.e. headless selenium), if needed.
        """
        ep = {
            urlparse(protocol.endpoint).netloc: key
            for key, protocol in PyCloud.endpoints.items()
        }
        code, hostname = tokenhandler(client_id).get_access_token()
        params = {"client_id": client_id, "client_secret": client_secret, "code": code}
        endpoint = ep.get(hostname)
        endpoint_url = PyCloud.endpoints.get(endpoint).endpoint
        resp = httpx.get(endpoint_url + "oauth2_token", params=params).json()
        access_token = resp.get("access_token")
        return cls("", access_token, endpoint, token_expire, oauth2=True)

    def _do_request(self, method, authenticate=True, json=True, endpoint=None, **kw):
        return self.connection.do_get_request(
            method, authenticate, json, endpoint, **kw
        )
    
    def _init_crypto_keys(self):
        """Initialize crypto keys by fetching user keys from pCloud."""
        if not self.crypto_password:
            return
        
        log.info("Fetching crypto user keys...")
        resp = self._do_request("crypto_getuserkeys")
        
        if "privatekey" not in resp or "publickey" not in resp:
            raise ValueError("Failed to fetch crypto user keys")
        
        private_key = resp["privatekey"]
        public_key = resp["publickey"]
        
        log.info("Decrypting private key...")
        self.keypair = decrypt_private_key(
            self.crypto_password,
            private_key,
            public_key
        )
        log.info("Crypto keys initialized successfully.")

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
        default_api = self.endpoints.get("api").endpoint
        resp = self._do_request(
            "getapiserver", authenticate=False, endpoint=default_api
        )

        api = resp.get("api","")
        if len(api):
            return urlunsplit(["https", api[0], "/", "", ""])
        else:
            return default_api

    @RequiredParameterCheck(("language",))
    def setlanguage(self, **kwargs):
        return self._do_request("setlanguage", **kwargs)

    @RequiredParameterCheck(("mail", "reason", "message"), mode=MODE_AND)
    def feedback(self, **kwargs):
        return self._do_request("feedback", **kwargs)

    def currentserver(self):
        return self._do_request("currentserver")

    def diff(self, **kwargs):
        return self._do_request("diff", **kwargs)

    def getfilehistory(self, **kwargs):
        return self._do_request("getfilehistory", **kwargs)

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
        result = self._do_request("listfolder", **kwargs)
        
        # Check if folder is encrypted and decrypt filenames if needed
        if self.keypair and result.get("metadata", {}).get("encrypted"):
            try:
                self._decrypt_folder_contents(result["metadata"])
            except Exception as e:
                log.warning(f"Failed to decrypt folder contents: {e}")
        
        return result
    
    def _decrypt_folder_contents(self, metadata):
        """Recursively decrypt filenames in folder metadata."""
        if not CRYPTO_AVAILABLE or not self.keypair:
            return
        
        # Get the folder ID
        folderid = metadata.get("folderid")
        if not folderid:
            log.warning("Cannot decrypt folder: no folderid found")
            return
        
        # Fetch the encrypted folder key from pCloud
        try:
            key_response = self._do_request("crypto_getfolderkey", folderid=folderid)
            encrypted_key = key_response.get("key")
            if not encrypted_key:
                log.warning(f"No encryption key returned for folder {folderid}")
                return
        except Exception as e:
            log.warning(f"Failed to fetch folder key for folder {folderid}: {e}")
            return
        
        # Decrypt the folder key
        try:
            folder_key = self.keypair.decrypt_folder_key(encrypted_key)
            # cache for later content decryption
            self._folder_key_cache[folderid] = folder_key
        except Exception as e:
            log.warning(f"Failed to decrypt folder key: {e}")
            return
        
        # Decrypt file and folder names in contents
        contents = metadata.get("contents", [])
        for item in contents:
            if item.get("encrypted") and decrypt_filename:
                encrypted_name = item.get("name", "")
                try:
                    decrypted_name = decrypt_filename(encrypted_name, folder_key)
                    item["name"] = decrypted_name
                except Exception as e:
                    log.warning(f"Failed to decrypt filename '{encrypted_name}': {e}")
            
            # Recursively decrypt subfolders
            if item.get("isfolder") and item.get("encrypted"):
                self._decrypt_folder_contents(item)

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
    @RequiredParameterCheck(("files", "data"))
    def uploadfile(self, **kwargs):
        """upload a file to pCloud

        1) You can specify a list of filenames to upload
        files=['/home/pcloud/foo.txt', '/home/pcloud/bar.txt']

        2) you can specify binary data via the data parameter and
        need to specify the filename too
        data=b'Hello pCloud', filename='foo.txt'
        """
        if "files" in kwargs:
            upload_files = kwargs.pop("files", [])
            files = [
                ("file", (os.path.split(f)[1], open(f, "rb"))) for f in upload_files
            ]
        else:  # 'data' in kwargs:
            files = [
                (
                    "file",
                    (
                        kwargs.pop("filename", "data-upload.bin"),
                        BytesIO(kwargs.pop("data")),
                    ),
                )
            ]
        if "folderid" in kwargs:
            # cast folderid to string, since API allows this but requests not
            kwargs["folderid"] = str(kwargs["folderid"])
        return self.connection.upload("uploadfile", files, **kwargs)

    @RequiredParameterCheck(("progresshash",))
    def uploadprogress(self, **kwargs):
        return self._do_request("uploadprogress", **kwargs)

    @RequiredParameterCheck(("url",))
    def downloadfile(self, **kwargs):
        return self._do_request("downloadfile", **kwargs)

    @RequiredParameterCheck(("url",))
    def downloadfileasync(self, **kwargs):
        return self._do_request("downloadfileasync", **kwargs)

    @RequiredParameterCheck(("path", "fileid"))
    def copyfile(self, **kwargs):
        return self._do_request("copyfile", **kwargs)

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
    @RequiredParameterCheck(("path", "folderid"))
    @RequiredParameterCheck(("mail", "permissions"), mode=MODE_AND)
    def sharefolder(self, **kwargs):
        return self._do_request("sharefolder", **kwargs)

    def listshares(self, **kwargs):
        return self._do_request("listshares", **kwargs)

    # Public links
    def getfilepublink(self, **kwargs):
        raise OnlyPcloudError(ONLY_PCLOUD_MSG)

    def getpublinkdownload(self, **kwargs):
        raise OnlyPcloudError(ONLY_PCLOUD_MSG)

    @RequiredParameterCheck(("path", "folderid"))
    def gettreepublink(self, **kwargs):
        raise NotImplementedError

    @RequiredParameterCheck(("code",))
    def showpublink(self, **kwargs):
        return self._do_request("showpublink", authenticate=False, **kwargs)

    @RequiredParameterCheck(("code",))
    def copypubfile(self, **kwargs):
        return self._do_request("copypubfile", **kwargs)

    def listpublinks(self, **kwargs):
        return self._do_request("listpublinks", **kwargs)

    def listplshort(self, **kwargs):
        return self._do_request("listplshort", **kwargs)

    @RequiredParameterCheck(("linkid",))
    def deletepublink(self, **kwargs):
        return self._do_request("deletepublink", **kwargs)

    @RequiredParameterCheck(("linkid",))
    def changepublink(self, **kwargs):
        return self._do_request("changepublink", **kwargs)

    @RequiredParameterCheck(("path", "folderid"))
    def getfolderpublink(self, **kwargs):
        expire = kwargs.get("expire")
        if expire is not None:
            kwargs["expire"] = to_api_datetime(expire)
        return self._do_request("getfolderpublink", **kwargs)

    @RequiredParameterCheck(("code",))
    def getpubzip(self, unzip=False, **kwargs):
        zipresponse = self._do_request(
            "getpubzip", authenticate=False, json=False, **kwargs
        )
        if not unzip:
            return zipresponse
        zipfmem = BytesIO(zipresponse)
        code = kwargs.get("code")
        try:
            zf = zipfile.ZipFile(zipfmem)
        except zipfile.BadZipfile:
            # Could also be the case, if public link is password protected.
            log.warn(
                f"No valid zipfile found for code f{code}. Empty content is returned."
            )
            return ""
        names = zf.namelist()
        if names:
            contents = zf.read(names[0])
        else:
            log.warn(f"Zip file is empty for code f{code}. Empty content is returned.")
            contents = ""
        return contents

    # Trash methods
    def trash_list(self, **kwargs):
        return self._do_request("trash_list", **kwargs)

    @RequiredParameterCheck(("fileid", "folderid"))
    def trash_clear(self, **kwargs):
        return self._do_request("trash_clear", **kwargs)

    @RequiredParameterCheck(("fileid", "folderid"))
    def trash_restorepath(self, **kwargs):
        return self._do_request("trash_restorepath", **kwargs)

    @RequiredParameterCheck(("fileid", "folderid"))
    def trash_restore(self, **kwargs):
        return self._do_request("trash_restore", **kwargs)

    # convenience methods
    @RequiredParameterCheck(("query",))
    def search(self, **kwargs):
        return self._do_request("search", **kwargs)

    @RequiredParameterCheck(("path",))
    def file_exists(self, **kwargs):
        path = kwargs["path"]
        resp = self.stat(path=path)
        result = resp.get("result")
        if result == 0:
            return True
        elif result in (2001, 2055):
            return False
        else:
            raise OSError(f"pCloud error occured ({result}) - {resp['error']}:  {path}")

    @RequiredParameterCheck(("fileid",))
    def file_download(self, **kwargs):
        fileid = kwargs.get("fileid")
        resp = self.stat(fileid=fileid, use_session=True)
        result = resp.get("result")
        if result == 0:
            metadata = resp["metadata"]
            filename = metadata["name"]
        else:
            raise OSError(
                f"pCloud error occured ({result}) - {resp.get('error','')}:  {fileid}"
            )

        zip_bytes = self.getzip(fileids=[fileid], use_session=True)
        try:
            with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
                data = zf.read(filename)
        except zipfile.BadZipFile:
            raise OSError(f"Data: {zip_bytes}")

        # If file is encrypted and we have crypto set up, decrypt the contents
        try:
            if (
                CRYPTO_AVAILABLE
                and self.keypair is not None
                and resp.get("metadata", {}).get("encrypted")
                and decrypt_file_contents is not None
            ):
                # Fetch per-file CEK via getfilelink?getkey=1
                file_key = self._get_file_key(fileid)
                if file_key:
                    return decrypt_file_contents(data, file_key)
        except Exception as e:
            # Don't fail downloads if decryption fails; return raw data
            log.warning(f"Failed to decrypt encrypted file {fileid}: {e}")
            return data

        return data

    def _get_folder_key(self, folderid):
        """Retrieve and cache the decrypted FolderKey for a folder id."""
        if not CRYPTO_AVAILABLE or not self.keypair:
            return None
        if folderid in self._folder_key_cache:
            return self._folder_key_cache[folderid]
        try:
            key_response = self._do_request("crypto_getfolderkey", folderid=folderid)
            encrypted_key = key_response.get("key")
            if not encrypted_key:
                log.warning(f"No encrypted key for folder {folderid}")
                return None
            folder_key = self.keypair.decrypt_folder_key(encrypted_key)
            self._folder_key_cache[folderid] = folder_key
            return folder_key
        except Exception as e:
            log.warning(f"Failed to get/decrypt folder key for {folderid}: {e}")
            return None

    def _get_file_key(self, fileid):
        """Retrieve and cache the decrypted CEK for a file via getfilelink(getkey=1)."""
        if not CRYPTO_AVAILABLE or not self.keypair:
            return None
        if fileid in self._file_key_cache:
            return self._file_key_cache[fileid]
        try:
            resp = self._do_request("getfilelink", fileid=fileid, getkey=1)
            encrypted_key = resp.get("key") if isinstance(resp, dict) else None
            if not encrypted_key:
                # Some variants nest key in metadata; handle robustly
                encrypted_key = (
                    resp.get("metadata", {}).get("key")
                    if isinstance(resp, dict) else None
                )
            if not encrypted_key:
                log.warning(f"No encrypted key returned for file {fileid}")
                return None
            # Decrypt using RSA private key
            if hasattr(self.keypair, "decrypt_file_key") and self.keypair.decrypt_file_key:
                file_key = self.keypair.decrypt_file_key(encrypted_key)
            else:
                # fallback to folder-style CEK decrypt if method absent
                file_key = self.keypair.decrypt_folder_key(encrypted_key)
            self._file_key_cache[fileid] = file_key
            return file_key
        except Exception as e:
            log.warning(f"Failed to get/decrypt file key for {fileid}: {e}")
            return None


# EOF
