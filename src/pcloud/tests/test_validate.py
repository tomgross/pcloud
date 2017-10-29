import pytest
from pcloud.validate import RequiredParameterCheck


@RequiredParameterCheck(('path', 'folderid'))
def foo(self, path=None, folderid=None, bar=None):
    return (path, folderid, bar)


class TestPathIdentifier(object):

    def test_validiate_path(self):
        assert foo(None, path='/', bar='x') == ('/', None, 'x')

    def test_validiate_folderid(self):
        assert foo(None, folderid='0') == (None, '0', None)

    def test_validiate_nothing(self):
        with pytest.raises(ValueError):
            foo(None, bar='something')
