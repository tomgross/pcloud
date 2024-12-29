# -*- coding: utf-8 -*-
import io
import os
import tempfile

from contextlib import closing
from datetime import datetime
from fs import errors
from fs.enums import ResourceType
from fs.base import FS
from fs.info import Info
from fs.opener import Opener
from fs.path import abspath
from fs.path import dirname
from fs.mode import Mode
from fs.subfs import SubFS
from pcloud import api


DT_FORMAT_STRING = "%a, %d %b %Y %H:%M:%S %z"

FSMODEMMAP = {
    "w": api.O_WRITE,
    "x": api.O_EXCL,
    "a": api.O_APPEND,
    "r": api.O_WRITE,  # pCloud does not have a read mode
}


class PCloudFile(io.IOBase):
    """Proxy for a pCloud file."""

    @classmethod
    def factory(cls, path, mode, on_close):
        """Create a S3File backed with a temporary file."""
        _temp_file = tempfile.TemporaryFile()
        proxy = cls(_temp_file, path, mode, on_close=on_close)
        return proxy

    def __repr__(self):
        return _make_repr(self.__class__.__name__, self.filename, self.__mode)

    def __init__(self, f, filename, mode, on_close=None):
        self._f = f
        self.filename = filename
        self.__mode = mode
        self.is_truncated = False
        self._on_close = on_close

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    @property
    def raw(self):
        return self._f

    def close(self):
        if self._on_close is not None:
            self._on_close(self)

    @property
    def closed(self):
        return self._f.closed

    def fileno(self):
        return self._f.fileno()

    def flush(self):
        return self._f.flush()

    def isatty(self):
        return self._f.asatty()

    def readable(self):
        return self.__mode.reading

    def readline(self, limit=-1):
        return self._f.readline(limit)

    def readlines(self, hint=-1):
        if hint == -1:
            return self._f.readlines(hint)
        else:
            size = 0
            lines = []
            for line in iter(self._f.readline, b""):
                lines.append(line)
                size += len(line)
                if size > hint:
                    break
            return lines

    def seek(self, offset, whence=os.SEEK_SET):
        if whence not in (os.SEEK_CUR, os.SEEK_END, os.SEEK_SET):
            raise ValueError("invalid value for 'whence'")
        self._f.seek(offset, whence)
        return self._f.tell()

    def seekable(self):
        return True

    def tell(self):
        return self._f.tell()

    def writable(self):
        return self.__mode.writing

    def writelines(self, lines):
        return self._f.writelines(lines)

    def read(self, n=-1):
        if not self.__mode.reading:
            raise IOError("not open for reading")
        return self._f.read(n)

    def readall(self):
        return self._f.readall()

    def readinto(self, b):
        return self._f.readinto(b)

    def write(self, b):
        if not self.__mode.writing:
            raise IOError("not open for writing")
        self._f.write(b)
        return len(b)

    def truncate(self, size=None):
        if size is None:
            size = self._f.tell()
        self._f.truncate(size)
        self.is_truncated = True
        return size

    @property
    def mode(self):
        return self.__mode.to_platform_bin()


class PCloudSubFS(SubFS):
    def __init__(self, parent_fs, path):
        super().__init__(parent_fs, path)
        if not hasattr(self._wrap_fs, "_wrap_sub_dir"):
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
        "thread_safe": True,
        "unicode_paths": True,
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
        with self._lock:
            resp = self.pcloud.stat(path=_path)
        metadata = resp.get("metadata", None)
        if metadata is None:
            raise errors.ResourceNotFound(path=_path)
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
        with self._lock:
            result = self.pcloud.listfolder(path=_path)
        return [item["name"] for item in result["metadata"]["contents"]]

    def makedir(self, path, permissions=None, recreate=False):
        self.check()
        subpath = getattr(self, "_wrap_sub_dir", "")
        path = abspath(path)
        if path == "/" or path == subpath or self.exists(path):
            if recreate:
                return self.opendir(path)
            else:
                raise errors.DirectoryExists(path)
        with self._lock:
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
                path=path,
                msg=f"Create of directory failed with ({result}) {resp['error']}",
            )
        else:  # everything is OK
            return self.opendir(path, metadata=resp["metadata"])

    def opendir(self, path, factory=None, metadata=None):
        """override method from fs.base"""
        from fs.subfs import SubFS

        _factory = factory or self.subfs_class or SubFS

        if metadata is not None:
            is_dir = metadata.get("isfolder", False)
        else:
            is_dir = self.getinfo(path).is_dir
        if not is_dir:
            raise errors.DirectoryExpected(path=path)
        return _factory(self, path)

    def openbin(
        self, path: str, mode: str = "r", buffering: int = -1, **options
    ) -> "PCloudFile":
        _mode = Mode(mode)
        _mode.validate_bin()
        self.check()
        _path = self.validatepath(path)
        for pyflag, pcloudflag in FSMODEMMAP.items():
            if pyflag in mode:
                flags = pcloudflag
                break
        else:
            raise api.InvalidFileModeError

        def on_close(pcloudfile):
            if _mode.create or _mode.writing:
                pcloudfile.raw.seek(0)
                data = pcloudfile.raw.read()
                resp = self.pcloud.uploadfile(
                    path=dirname(_path),
                    data=data,
                    filename=pcloudfile.filename,
                )
                if resp.get("result") != 0:
                    api.log.error(f"Upload Error for file {_path}: {resp}")
                    return
            pcloudfile.raw.close()

        if _mode.create:
            dir_path = dirname(_path)
            if dir_path != "/":
                self.getinfo(path=dir_path)
            try:
                info = self.getinfo(path, namespaces=["details"])
            except errors.ResourceNotFound:
                pass
            else:
                if _mode.exclusive:
                    raise errors.FileExists(path)
                if info.is_dir:
                    raise errors.FileExpected(path)

            pcloud_file = PCloudFile.factory(path, _mode, on_close=on_close)

            if _mode.appending:
                resp = self.pcloud.file_open(path=_path, flags=flags)
                fd = resp.get("fd")
                if fd is not None:
                    data = self.pcloud.file_read(fd=fd, count=info.size)
                    if resp.get("result") != 0:
                        api.log.error(f"Error reading file {_path} failed with {resp}")
                    pcloud_file.seek(0, os.SEEK_END)
                    pcloud_file.raw.write(data)
                    resp = self.pcloud.file_close(fd=fd)
                else:
                    api.log.error(f"No open file found to write. {resp}")

            return pcloud_file

        info = self.getinfo(_path, namespaces=["details"])
        if info.is_dir:
            raise errors.FileExpected(_path)

        pcloud_file = PCloudFile.factory(_path, _mode, on_close=on_close)
        resp = self.pcloud.file_open(path=_path, flags=api.O_WRITE)
        fd = resp.get("fd")
        if fd is None:
            api.log.error(f"Error opening file {_path} failed with {resp}")
        else:
            data = self.pcloud.file_read(fd=fd, count=info.size)
            pcloud_file.raw.write(data)
            resp = self.pcloud.file_close(fd=fd)
            if resp.get("result") != 0:
                api.log.error(f"Error closing file {_path} failed with {resp}")

        pcloud_file.seek(0)
        return pcloud_file

    def remove(self, path):
        _path = self.validatepath(path)
        if not self.exists(_path):
            raise errors.ResourceNotFound(path=_path)
        if self.getinfo(_path).is_dir:
            raise errors.FileExpected(_path)
        with self._lock:
            resp = self.pcloud.deletefile(path=_path)
            if resp["result"] != 0:
                api.log.error(f"Removing of file {_path} failed {resp}")

    def removedir(self, path):
        _path = self.validatepath(path)
        if not self.exists(_path):
            raise errors.ResourceNotFound(path=_path)
        info = self.getinfo(_path)
        if not info.is_dir:
            raise errors.DirectoryExpected(_path)
        if not self.isempty(_path):
            raise errors.DirectoryNotEmpty(_path)
        with self._lock:
            resp = self.pcloud.deletefolder(path=_path)
        if resp["result"] != 0:
            api.log.error(f"Removing of folder {_path} failed {resp}")

    def removetree(self, dir_path):
        _path = self.validatepath(dir_path)
        if not self.exists(_path):
            raise errors.ResourceNotFound(path=_path)
        if not self.getinfo(_path).is_dir:
            raise errors.DirectoryExpected(_path)
        with self._lock:
            resp = self.pcloud.deletefolderrecursive(path=_path)
        if resp["result"] != 0:
            api.log.error(f"Recurrsive removing of folder {_path} failed {resp}")


class PCloudOpener(Opener):
    protocols = ["pcloud", "pcloud+eapi"]

    @staticmethod
    def open_fs(fs_url, parse_result, writeable, create, cwd):
        _, _, directory = parse_result.resource.partition("/")
        endpoint = "api"
        if "+" in parse_result.protocol:
            _, endpoint = parse_result.protocol.split("+")
        fs = PCloudFS(
            username=parse_result.username,
            password=parse_result.password,
            endpoint=endpoint,
        )
        if directory:
            return fs.opendir(directory)
        else:
            return fs


def _make_repr(class_name, *args, **kwargs):
    """Generate a repr string. Identical to S3FS implementation

    Positional arguments should be the positional arguments used to
    construct the class. Keyword arguments should consist of tuples of
    the attribute value and default. If the value is the default, then
    it won't be rendered in the output.

    Here's an example::

        def __repr__(self):
            return make_repr('MyClass', 'foo', name=(self.name, None))

    The output of this would be something line ``MyClass('foo',
    name='Will')``.

    """
    arguments = [repr(arg) for arg in args]
    arguments.extend(
        "{}={!r}".format(name, value)
        for name, (value, default) in sorted(kwargs.items())
        if value != default
    )
    return "{}({})".format(class_name, ", ".join(arguments))


# EOF
