# -*- coding: utf-8 -*-
from fs.base import FS
from fs.info import Info
from fs.opener import Opener
from fs import errors
from fs.enums import ResourceType
from fs.path import abspath, dirname
from fs.mode import Mode
from fs.subfs import SubFS
import io
import array
import threading
from pcloud import api
from fs.enums import ResourceType, Seek
from contextlib import closing

from datetime import datetime

DT_FORMAT_STRING = "%a, %d %b %Y %H:%M:%S %z"

FSMODEMMAP = {
    'w': api.O_WRITE,
    'x': api.O_EXCL,
    'a': api.O_APPEND,
    'r': api.O_APPEND  # pCloud does not have a read mode
}


class PCloudFile(io.RawIOBase):
    """A file representation for pCloud files"""

    def __init__(self, pcloud, path, mode, encoding='utf-8'):
        self.pcloud = pcloud
        self.path = path
        self.mode = Mode(mode)
        self.encoding = encoding
        self._lock = threading.Lock()
        self._lines = None
        self._index = 0
        self.pos = 0
        for pyflag, pcloudflag in FSMODEMMAP.items():
            if pyflag in mode:
                flags = pcloudflag
                break
        else:
            raise api.InvalidFileModeError
        
        # Python and PyFS will create a file, which doesn't exist
        # but pCloud does not.
        if not self.pcloud.file_exists(path=self.path):
            resp = self.pcloud.file_open(path=self.path, flags=api.O_CREAT)
            self.pcloud.file_close(fd=resp["fd"])
        resp = self.pcloud.file_open(path=self.path, flags=flags)
        result = resp.get("result")
        if result == 0:
            self.fd = resp["fd"]
        elif result == 2009:
            raise errors.ResourceNotFound(path)
        else:
            raise OSError(f"pCloud error occured ({result}) - {resp['error']}:  {path}")

    def close(self):
        self.pcloud.file_close(fd=self.fd)
        self.fd = None

    def tell(self):
        return self.pos
    
    def seekable(self):
        return True

    def readable(self):
        return self.mode.reading
    
    def writable(self):
        return self.mode.writing
    
    @property
    def closed(self):
        return self.fd is None

    def seek(self, offset, whence=Seek.set):
        _whence = int(whence)
        if _whence not in (Seek.set, Seek.current, Seek.end):
            raise ValueError("invalid value for whence")
        if _whence == Seek.set:
            new_pos = offset
        elif _whence == Seek.current:
            new_pos = self.pos + offset
        elif _whence == Seek.end:
            resp = self.pcloud.file_size(fd=self.fd)
            file_size = resp["size"]
            new_pos = file_size + offset
        self.pos = max(0, new_pos)
        resp = self.pcloud.file_seek(fd=self.fd, offset=self.pos)
        return resp["offset"]
        # return self.tell()

    def read(self, size=-1):
        # print(f"pos: {self.pos} fd: {self.fd}")
        if not self.mode.reading:
            raise IOError("File not open for reading")
        if size == -1:
            size = self.pcloud.file_size(fd=self.fd)["size"]
        self.pos += size
        resp = self.pcloud.file_read(fd=self.fd, count=size)
        return resp
    
    def _close_and_reopen(self):
        self.pcloud.file_close(fd=self.fd)
        resp = self.pcloud.file_open(path=self.path, flags=api.O_APPEND)
        result = resp.get("result")
        if result == 0:
            self.fd = resp["fd"]

    def truncate(self, size=None):    
        with self._lock:
            if size is None:
                size = self.tell()
            self.pcloud.file_truncate(fd=self.fd, length=size)
            # file gets truncated on close
            self._close_and_reopen()
        return size

    def write(self, b):
        with self._lock:
            if not self.mode.writing:
                raise IOError("File not open for writing")
            if isinstance(b, str):
                b = bytes(b, self.encoding)
            #if b==b'O':
            #    import pdb; pdb.set_trace()
            resp = self.seek(self.pos-1)
            result = self.pcloud.file_write(fd=self.fd, data=b)
            sent_size = result["bytes"]
            self.pos += sent_size
            self._close_and_reopen()
        return sent_size

    def writelines(self,lines):
        self.write(b''.join(lines))

    def readline(self):
        result = b''
        char = ''
        while char != b'\n':
            char = self.read(size=1)
            print(char)
            result += char
            if not char:
                break
        return result
    
    def line_iterator(self, size=None):
        self.pcloud.file_seek(fd=self.fd, offset=0, whence=0)
        line = []
        byte = b"1"
        if size is None or size < 0:
            while byte:
                byte = self.read(1)
                line.append(byte)
                if byte in b"\n":
                    yield b"".join(line)
                    del line[:]
        else:
            while byte and size:
                byte = self.read(1)
                size -= len(byte)
                line.append(byte)
                if byte in b"\n" or not size:
                    yield b"".join(line)
                    del line[:]
    
    def readlines(self, hint=-1):
        lines = []
        size = 0
        for line in self.line_iterator():  # type: ignore
            lines.append(line)
            size += len(line)
            if hint != -1 and size > hint:
                break    
        return lines
    
    def readinto(self, buffer):
        data = self.read(len(buffer))
        bytes_read = len(data)
        if isinstance(buffer, array.array):
            buffer[:bytes_read] = array.array(buffer.typecode, data)
        else:
            buffer[:bytes_read] = data  # type: ignore
        return bytes_read

    def __repr__(self):
        return f"<pCloud file fd={self.fd} path={self.path} mode={self.mode}>"
    
    def __iter__(self):
        return iter(self.readlines())
    
    def __next__(self):
        if self._lines is None:
            self._lines = self.readlines()
        if self._index >= len(self._lines):
            raise StopIteration
        result = self._lines[self._index]
        self._index += 1
        return result

class PCloudSubFS(SubFS):

    def __init__(self, parent_fs, path):
        super().__init__(parent_fs, path)
        self._wrap_fs._wrap_sub_dir = self._sub_dir
        

class PCloudFS(FS):
    """A Python virtual filesystem representation for pCloud"""

    # make alternative implementations possible (i.e. for testing)
    factory = api.PyCloud
    subfs_class = PCloudSubFS

    _meta = {
        "invalid_path_chars": "\0:",
        "case_insensitive": False,
        "max_path_length": None,  # don't know what the limit is
        "max_sys_path_length": None,  # there's no syspath
        "supports_rename": False,  # since we don't have a syspath...
        "network": True,
        "read_only": False,
#        "thread_safe": True,
#        "unicode_paths": True,
        "virtual": False,
    }

    def __init__(self, username, password, endpoint="api"):
        super().__init__()
        self.pcloud = self.factory(username, password, endpoint)

    def __repr__(self):
        return "<pCloudFS>"
    
    def _to_datetime(self, dt_str, dt_format=DT_FORMAT_STRING):
        return datetime.strptime(dt_str, dt_format).timestamp()

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
                "modified": self._to_datetime(metadata.get("modified")),
                "created": self._to_datetime(metadata.get("created")),
                "metadata_changed": self._to_datetime(metadata.get("modified")),
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
        if not self.exists(path):
            raise errors.ResourceNotFound(path)
        
    def create(self, path, wipe=False):
        with self._lock:
            if self.exists(path) and not wipe:
                return False
            with closing(self.open(path, "wb")) as f:
                if wipe:
                    f.truncate(size=0)
            return True

    def listdir(self, path):
        _path = self.validatepath(path)
        _type = self.gettype(_path)
        if _type is not ResourceType.directory:
            raise errors.DirectoryExpected(path)
        result = self.pcloud.listfolder(path=_path)
        return [item["name"] for item in result["metadata"]["contents"]]
    
    def makedir(self, path, permissions=None, recreate=False):
        self.check()
        # import pdb; pdb.set_trace()
        subpath = getattr(self, '_wrap_sub_dir', '')
        if path == '/' or path == '.' or path == subpath:
            if recreate:
                return self.opendir(path)
            else:
                raise errors.DirectoryExists(path)        
        path = abspath(path)
        if self.exists(path):
            import pdb; pdb.set_trace()
            self.exists(path)
            raise errors.DirectoryExists(path)
        resp = self.pcloud.createfolder(path=path)
        result = resp["result"]
        if result == 2004:
            if recreate:
                # If the directory already exists and recreate = True
                # we don't want to raise an error
                pass
            else:
                raise errors.DirectoryExists(path)
        elif result == 2002:
            raise errors.ResourceNotFound(path)
        elif result != 0:
            raise errors.OperationFailed(
                path=path, msg=f"Create of directory failed with ({result}) {resp['error']}"
            )
        else:  # everything is OK
            return self.opendir(path)
        
    def openbin(self, path, mode="r", buffering=-1, **options):
        _mode = Mode(mode)
        _mode.validate_bin()
        _path = self.validatepath(path)
        if _path == "/":
            raise errors.FileExpected(path)
        with self._lock:
            try:
                info = self.getinfo(_path)
            except errors.ResourceNotFound:
                if _mode.reading:
                    raise errors.ResourceNotFound(path)
                if _mode.writing and not self.isdir(dirname(_path)):
                    raise errors.ResourceNotFound(path)
            else:
                if info.is_dir:
                    raise errors.FileExpected(path)
                if _mode.exclusive:
                    raise errors.FileExists(path)
            pcloud_file = PCloudFile(self.pcloud, _path, _mode.to_platform_bin())
        return pcloud_file

    def remove(self, path):
        _path = self.validatepath(path)
        if not self.exists(_path):
            raise errors.ResourceNotFound(path=_path)
        if self.getinfo(_path).is_dir == True:
            raise errors.FileExpected(_path)
        self.pcloud.deletefile(path=_path)

    def removedir(self, path):
        _path = self.validatepath(path)
        if not self.exists(_path):
            raise errors.ResourceNotFound(path=_path)
        info = self.getinfo(_path)
        if info.is_dir == False:
            raise errors.DirectoryExpected(_path)
        if not self.isempty(_path):
            raise errors.DirectoryNotEmpty(_path)
        self.pcloud.deletefolder(path=_path)

    def removetree(self, dir_path):
        _path = self.validatepath(dir_path)
        if not self.exists(_path):
            raise errors.ResourceNotFound(path=_path)
        if self.getinfo(_path).is_dir == False:
            raise errors.DirectoryExpected(_path)
        self.pcloud.deletefolderrecursive(path=_path)


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
