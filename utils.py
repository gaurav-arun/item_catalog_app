import string
import random
import json


def get_random_state(length=32):
    state = ''.join(random.choice(string.ascii_uppercase + string.ascii_lowercase + string.digits)
                    for _ in range(length))
    return state


def get_google_client_id(secret_file='client_secrets.json'):
    secret = json.loads(open(secret_file, 'r').read())
    return secret['web']['client_id']


def get_fb_app_id(secret_file='fb_client_secrets.json'):
    secret = json.loads(open(secret_file, 'r').read())
    return secret['app_id']


def get_fb_app_secret(secret_file='fb_client_secrets.json'):
    secret = json.loads(open(secret_file, 'r').read())
    return secret['app_secret']
