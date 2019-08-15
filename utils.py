import json
import random
import string
import sys


def get_random_state(length=32):
    state = ''.join(random.choice(string.ascii_uppercase + string.ascii_lowercase + string.digits)
                    for _ in range(length))
    return state


def get_google_client_id(secret_file='client_secrets.json'):
    try:
        secret = json.loads(open(secret_file, 'r').read())
        return secret['web']['client_id']
    except FileNotFoundError:
        print('Please make sure you have placed "{}" in the root directory.\n'
              'You can get more information on how to create this file in the README section\n'
              'of this repo: https://github.com/grathore07/item_catalog_app'.format(secret_file))
        sys.exit(-1)


def get_fb_app_id(secret_file='fb_client_secrets.json'):
    try:
        secret = json.loads(open(secret_file, 'r').read())
        return secret['app_id']
    except FileNotFoundError:
        print('Please make sure you have placed "{}" in the root directory.\n'
              'You can get more information on how to create this file in the README section\n'
              'of this repo: https://github.com/grathore07/item_catalog_app'.format(secret_file))
        sys.exit(-1)


def get_fb_app_secret(secret_file='fb_client_secrets.json'):
    try:
        secret = json.loads(open(secret_file, 'r').read())
        return secret['app_secret']
    except FileNotFoundError:
        print('Please make sure you have placed "{}" in the root directory.\n'
              'You can get more information on how to create this file in the README section\n'
              'of this repo: https://github.com/grathore07/item_catalog_app'.format(secret_file))
        sys.exit(-1)
