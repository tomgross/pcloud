import pytest
from pcloud.validate import RequiredParameterCheck
from pcloud.validate import MODE_AND


@RequiredParameterCheck(("path", "folderid"))
def foo(path=None, folderid=None, bar=None):
    return path, folderid, bar


@RequiredParameterCheck(("path", "folderid"), mode=MODE_AND)
def foo_all(path=None, folderid=None, bar=None):
    return path, folderid, bar


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
