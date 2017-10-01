#
from pcloud import api
from pcloud.tests.server import MockHandler
from pcloud.tests.server import MockServer

import threading


PORT = 5000


httpd = MockServer(("", PORT), MockHandler)
httpd_thread = threading.Thread(target=httpd.serve_forever)
httpd_thread.setDaemon(True)
httpd_thread.start()


class DummyPyCloud(api.PyCloud):

    endpoint = 'http://localhost:{0}/'.format(PORT)


def test_getdigest():
    api = DummyPyCloud('foo', 'bar')
    assert api.getdigest() == b'YGtAxbUpI85Zvs7lC7Z62rBwv907TBXhV2L867Hkh'


def test_get_auth_token():
    api = DummyPyCloud('foo', 'bar')
    assert api.get_auth_token() == 'TOKEN'


