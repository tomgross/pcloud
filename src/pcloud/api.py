from hashlib import sha1
from os.path import basename
from pcloud.validate import RequiredParameterCheck

import argparse
import logging
import requests
import sys

log = logging.getLogger('pycloud')


class AuthenticationError(Exception):
    """ Authentication failed """


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
        log.debug('Doing request to %s%s', self.endpoint, method)
        log.debug('Params: %s', params)
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
            'username': self.username.decode('utf-8'),
            'digest': digest.decode('utf-8'),
            'passworddigest': passworddigest.hexdigest()}
        resp = self._do_request('userinfo', authenticate=False, **params)
        if 'auth' not in resp:
            print(resp)
            raise(AuthenticationError)
        return resp['auth']

    # Folders
    @RequiredParameterCheck(('path', 'folderid'))
    def createfolder(self, **kwargs):
        return self._do_request('createfolder', **kwargs)

    @RequiredParameterCheck(('path', 'folderid'))
    def listfolder(self, **kwargs):
        return self._do_request('listfolder', **kwargs)

    @RequiredParameterCheck(('path', 'folderid'))
    def renamefolder(self, **kwargs):
        return self._do_request('renamefolder', **kwargs)

    @RequiredParameterCheck(('path', 'folderid'))
    def deletefolder(self, **kwargs):
        return self._do_request('deletefolder', **kwargs)

    @RequiredParameterCheck(('path', 'folderid'))
    def deletefolderrecursive(self, **kwargs):
        return self._do_request('deletefolderrecursive', **kwargs)

    # File
    @RequiredParameterCheck(('files',))
    def uploadfile(self, **kwargs):
        kwargs['filename'] = []
        kwargs['auth'] = self.auth_token
        for f in kwargs['files']:
            filename = basename(f)
            files = {filename: open(f, 'rb')}
            kwargs['filename'] = filename
        resp = requests.post(
            self.endpoint + 'uploadfile',
            files=files,
            data=kwargs)
        return resp.json()

    @RequiredParameterCheck(('progresshash',))
    def uploadprogress(self, **kwargs):
        return self._do_request('uploadprogress', **kwargs)

    @RequiredParameterCheck(('links',))
    def downloadfile(self, **kwargs):
        return self._do_request('downloadfile', **kwargs)

    def copyfile(self, **kwargs):
        pass

    def checksumfile(self, **kwargs):
        pass

    def deletefile(self, **kwargs):
        pass

    def renamefile(self, **kwargs):
        pass

    # Auth
    def sendverificationemail(self, **kwargs):
        pass

    def verifyemail(self, **kwargs):
        pass

    def changepassword(self, **kwargs):
        pass

    def lostpassword(self, **kwargs):
        pass

    def resetpassword(self, **kwargs):
        pass

    def register(self, **kwargs):
        pass

    def invite(self, **kwargs):
        pass

    def userinvites(self, **kwargs):
        pass

    def logout(self, **kwargs):
        pass

    def listtokens(self, **kwargs):
        pass

    def deletetoken(self, **kwargs):
        pass


if __name__ == '__main__':
    main()
