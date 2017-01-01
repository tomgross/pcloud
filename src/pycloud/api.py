from hashlib import sha1

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
    def createfolder(self, path=None, folderid=0, name=''):
        pass

    def listfolder(self, path=None, folderid=None):
        params = {}
        if folderid is not None:
            params['folderid'] = folderid
        elif path is not None:
            params['path'] = path
        else:
            raise('Either `folderid` or `path` must be specified!')
        api_method = sys._getframe().f_code.co_name
        return self._do_request(method, **params)
    
    def renamefolder(self):
        print(sys._getframe().f_code.co_name)

    deletefolder = listfolder
    deletefolderrecursive = listfolder


if __name__ == '__main__':
    main()
