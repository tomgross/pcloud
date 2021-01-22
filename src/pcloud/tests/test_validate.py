import pytest
from pcloud.validate import RequiredParameterCheck
from pcloud.validate import MODE_AND


@RequiredParameterCheck(("path", "folderid"))
def foo(path=None, folderid=None, bar=None):
    return path, folderid, bar


@RequiredParameterCheck(("path", "folderid"), mode=MODE_AND)
def foo_all(path=None, folderid=None, bar=None):
    return path, folderid, bar


@RequiredParameterCheck(("path", "fileid"))
@RequiredParameterCheck(("topath", "tofolderid"))
def extractarchive(path=None, fileid=None, topath=None, tofolderid=None, extra=None):
    return path, fileid, topath, tofolderid


class TestPathIdentifier(object):
    def test_validiate_path(self):
        assert foo(path="/", bar="x") == ("/", None, "x")

    def test_validiate_folderid(self):
        assert foo(folderid="0") == (None, "0", None)

    def test_validiate_nothing(self):
        with pytest.raises(ValueError):
            foo(bar="something")

    def test_validiate_all_path(self):
        with pytest.raises(ValueError):
            foo_all(path="/", bar="x")

    def test_validiate_all_folderid(self):
        with pytest.raises(ValueError):
            foo_all(folderid="0") == (None, "0", None)

    def test_validiate_all(self):
        foo_all(folderid="0", path="/") == ("/", "0", None)


class TestMultipleValidators(object):
    def test_single(self):
        with pytest.raises(ValueError):
            assert extractarchive(path="1", fileid=1)

    def test_all(self):
        assert extractarchive(path="/", fileid=1, topath="/a", tofolderid=2) == (
            "/",
            1,
            "/a",
            2,
        )

    def test_two(self):
        assert extractarchive(path="/", topath="/b") == ("/", None, "/b", None)
