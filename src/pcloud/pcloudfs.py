# -*- coding: utf-8 -*-
from fs.base import FS
from fs.info import Info
from fs.opener import Opener
from fs import errors
from fs.enums import ResourceType
from fs.path import abspath
from io import BytesIO
from pcloud import api

FSMODEMMAP = {
    'w': api.O_WRITE,
    'x': api.O_EXCL,
    'a': api.O_APPEND,
    'r': api.O_APPEND  # pCloud does not have a read mode
}

class PCloudFile(BytesIO):
    """A file representation for pCloud files"""

    def __init__(self, pcloud, path, mode, encoding='utf-8'):
        self.pcloud = pcloud
        self.path = path
        self.mode = mode
        self.encoding = encoding
        for pyflag, pcloudflag in FSMODEMMAP.items():
            if pyflag in mode:
                flags = pcloudflag
                break
        else:
            raise api.InvalidFileModeError

        if "t" in mode:
            self.binary = False
        else:
            self.binary = True

        # Python and PyFS will create a file, which doesn't exist
        # in append-mode `a` but pCloud does not.
        if flags == api.O_APPEND and not self.pcloud.file_exists(path=self.path):
            resp = self.pcloud.file_open(path=self.path, flags=api.O_CREAT)
            self.pcloud.file_close(fd=resp["fd"])
        resp = self.pcloud.file_open(path=self.path, flags=flags)
        result = resp.get("result")
        if result == 0:
            self.fd = resp["fd"]
        else:
            raise OSError(f"pCloud error occured ({result}) - {resp['error']}:  {path}")

    def close(self):
        self.pcloud.file_close(fd=self.fd)
        self.fd = None

    @property
    def closed(self):
        return self.fd is None

    def fileno(self):
        return self.fd

    def seek(self, offset, whence=None):
        self.pcloud.file_seek(fd=self.fd, offset=offset)

    def read(self, size=-1):
        if size == -1:
            size = self.pcloud.file_size(fd=self.fd)["size"]
        return self.pcloud.file_read(fd=self.fd, count=size)

    def truncate(self, size=None):
        self.pcloud.file_truncate(fd=self.fd)

    def write(self, b):
        if isinstance(b, str):
            b = bytes(b, self.encoding)
        self.pcloud.file_write(fd=self.fd, data=b)

class PCloudFS(FS):
    """A Python virtual filesystem representation for pCloud"""

    # make alternative implementations possible (i.e. for testing)
    factory = api.PyCloud

    def __init__(self, username, password, endpoint="api"):
        super().__init__()
        self.pcloud = self.factory(username, password, endpoint)
        self._meta = {
            "case_insensitive": False,
            "invalid_path_chars": ":",  # not sure what else
            "max_path_length": None,  # don't know what the limit is
            "max_sys_path_length": None,  # there's no syspath
            "network": True,
            "read_only": False,
            "supports_rename": False,  # since we don't have a syspath...
        }

    def __repr__(self):
        return "<pCloudFS>"

    def _info_from_metadata(self, metadata, namespaces):
        info = {
            "basic": {
                "is_dir": metadata.get("isfolder", False),
                "name": metadata.get("name"),
            }
        }
        if "details" in namespaces:
            info["details"] = {
                "type": 1 if metadata.get("isfolder") else 2,
                "accessed": None,
                "modified": metadata.get("modified"),
                "created": metadata.get("created"),
                "metadata_changed": metadata.get("modified"),
                "size": metadata.get("size", 0),
            }
        if "link" in namespaces:
            pass
        if "access" in namespaces:
            pass
        return Info(info)

    def getinfo(self, path, namespaces=None):
        self.check()
        namespaces = namespaces or ()
        _path = self.validatepath(path)
        # we strip the last item from the path to get
        # the parent folder. since the pCloud API
        # provides no consistent way of geting the metadata
        # for both folders and files we extract it from the
        # folder listing
        if path == "/":
            parent_path = "/"
        else:
            parent_path = "/".join(_path.split("/")[:-1])
            parent_path = parent_path if parent_path else "/"
        folder_list = self.pcloud.listfolder(path=parent_path)
        metadata = None
        if "metadata" in folder_list:
            if _path == "/":
                metadata = folder_list["metadata"]
            else:
                for item in folder_list["metadata"]["contents"]:
                    if item["path"] == _path:
                        metadata = item
                        break
        if metadata is None:
            raise errors.ResourceNotFound(path=path)
        return self._info_from_metadata(metadata, namespaces)

    def setinfo(self, path, info):  # pylint: disable=too-many-branches
        # pCloud doesn't support changing any of the metadata values
        pass

    def listdir(self, path):
        _path = self.validatepath(path)
        _type = self.gettype(_path)
        if _type is not ResourceType.directory:
            raise errors.DirectoryExpected(path)
        result = self.pcloud.listfolder(path=_path)
        return [item["name"] for item in result["metadata"]["contents"]]

    def makedir(self, path, permissions=None, recreate=False):
        self.check()
        if path == '/' or path == '.':
            return self.opendir(path)
        
        
        path = abspath(path)
        result = self.pcloud.createfolder(path=path)
        if result["result"] == 2004:
            if recreate:
                # If the directory already exists and recreate = True
                # we don't want to raise an error
                pass
            else:
                raise errors.DirectoryExists(path)
        elif result["result"] != 0:
            raise errors.OperationFailed(
                path=path, msg=f"Create of directory failed with {result['error']}"
            )
        else:  # everything is OK
            return self.opendir(path)
        
    def openbin(self, path, mode="r", buffering=-1, **options):
        if path == "/":
            raise errors.FileExpected(path)
        return PCloudFile(self.pcloud, path, mode)

    def remove(self, path):
        self.pcloud.deletefile(path=path)

    def removedir(self, path):
        self.pcloud.deletefolder(path=path)

    def removetree(self, dir_path):
        self.pcloud.deletefolderrecursive(path=dir_path)


class PCloudOpener(Opener):
    protocols = ["pcloud"]

    @staticmethod
    def open_fs(fs_url, parse_result, writeable, create, cwd):
        _, _, directory = parse_result.resource.partition("/")
        fs = PCloudFS(username=parse_result.username, password=parse_result.password)
        if directory:
            return fs.opendir(directory)
        else:
            return fs


# EOF
