import argparse
import requests
from hashlib import sha1


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

    # Authentication
    def getdigest(self):
        resp = requests.get(self.endpoint + 'getdigest')
        return bytes(resp.json()['digest'], 'utf-8')

    def get_auth_token(self):
        digest = self.getdigest()
        passworddigest = sha1(
            self.password +
            bytes(sha1(self.username).hexdigest(), 'utf-8') +
            digest)
        resp = requests.get(self.endpoint + 'userinfo',
                params={'getauth': 1,
                    'logout': 1,
                    'username': self.username,
                    'digest': digest,
                    'passworddigest': passworddigest.hexdigest()}
        )
        return resp.json()['auth']

    # Folders
    def listfolder(self, path=None, folderid=0):
        params = {'auth': self.auth_token}
        if path is not None:
            params['path'] = path
        else:
            params['folderid'] = folderid
        resp = requests.get(self.endpoint + 'listfolder', params=params)
        return resp.json()


if __name__ == '__main__':
    main()
