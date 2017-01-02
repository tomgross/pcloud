from hashlib import sha1
from pycloud.validate import RequiredParameterCheck

import argparse
import requests
import sys


def main():
    parser = argparse.ArgumentParser(description='pCloud command line client')
    parser.add_argument('username',
                    help='The username for login into your pCloud account')
    parser.add_argument('password',
                    help='The password for login into your pCloud account')
    args = parser.parse_args()
    pyc = PyCloud(args.username, args.password)


class PyCloud(object):

    endpoint = 'https://api.pcloud.com/'

    def __init__(self, username, password):
        self.username = username.lower().encode('utf-8')
        self.password = password.encode('utf-8')
        self.auth_token = self.get_auth_token()

    def _do_request(self, method, authenticate=True, **kw):
        if authenticate:
             params = {'auth': self.auth_token}
        else:
             params = {}
        params.update(kw)
        resp = requests.get(self.endpoint + method, params=params)
        return resp.json()


    # Authentication
    def getdigest(self):
        resp = self._do_request('getdigest', authenticate=False)
        return bytes(resp['digest'], 'utf-8')

    def get_auth_token(self):
        digest = self.getdigest()
        passworddigest = sha1(
            self.password +
            bytes(sha1(self.username).hexdigest(), 'utf-8') +
            digest)
        params={'getauth': 1,
            'logout': 1,
            'username': self.username,
            'digest': digest,
            'passworddigest': passworddigest.hexdigest()}
        resp = self._do_request('userinfo', authenticate=False, **params)
        return resp['auth']

    # Folders
    @RequiredParameterCheck(('path', 'folderid'))
    def createfolder(self, path=None, folderid=0, name=''):
        return self._do_request('createfolder', **kwargs)

    @RequiredParameterCheck(('path', 'folderid'))
    def listfolder(self, **kwargs):
        return self._do_request('listfolder', **kwargs)
    
    @RequiredParameterCheck(('path', 'folderid'))
    def renamefolder(self):
        return self._do_request('renamefolder', **kwargs)

    @RequiredParameterCheck(('path', 'folderid'))
    def deletefolder(self, **kwargs):
        return self._do_request('deletefolder', **kwargs)

    @RequiredParameterCheck(('path', 'folderid'))
    def deletefolderrecursive(self, **kwargs):
        return self._do_request('deletefolderrecursive', **kwargs)


if __name__ == '__main__':
    main()
