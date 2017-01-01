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
    pyc = PyCloud()
    print(pyc.get_auth_token(args.username, args.password))


class PyCloud(object):

    endpoint = 'https://api.pcloud.com/'

    def getdigest(self):
        resp = requests.get(self.endpoint + 'getdigest')
        return resp.json()['digest']

    def get_auth_token(self, username, password):
        digest = self.getdigest()
        l_username = bytes(username.lower(), 'utf-8')
        passworddigest = sha1(
            bytes(password, 'utf-8') +
            bytes(sha1(l_username).hexdigest(), 'utf-8') +
            bytes(digest, 'utf-8'))
        resp = requests.get(self.endpoint + 'userinfo',
                params={'getauth': 1,
                    'logout': 1,
                    'username': username,
                    'digest': digest,
                    'passworddigest': passworddigest.hexdigest()}
        )
        return resp.json()['auth']


if __name__ == '__main__':
    main()
