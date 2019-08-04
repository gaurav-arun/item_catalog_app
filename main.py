from flask import Flask, render_template, request, redirect, jsonify, url_for, flash
from flask import session as login_session
from flask_uploads import UploadSet, configure_uploads, IMAGES

from sqlalchemy import create_engine, asc
from sqlalchemy.orm import sessionmaker
from database_setup import Base, User, Item
from bbid import bbid
import os
import shutil
import utils

# from oauth2client.client import flow_from_clientsecrets
# from oauth2client.client import FlowExchangeError

import httplib2
from oauth2client import client

import json
from flask import make_response
import requests

photos = UploadSet('photos', IMAGES)

app = Flask(__name__)

APPLICATION_NAME = "Item Catalog Application"
CLIENT_SECRETS_FILE = 'client_secrets.json'
CLIENT_ID = json.loads(open(CLIENT_SECRETS_FILE, 'r').read())['web']['client_id']


# Connect to the database and create database session
engine = create_engine('sqlite:///db/itemcatalog.db')
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
session = DBSession()


@app.route('/')
@app.route('/login/')
def login():
    state = utils.get_random_state()
    login_session['state'] = state
    return render_template('login.html', STATE=state)


@app.route('/add-new-item', methods=['POST'])
def upload():
    item_img = request.files['item_img']
    item_name = request.form['item_name']
    item_cat = request.form['item_cat']
    item_desc = request.form['item_desc']

    if item_img:
        item_img_content = item_img.read()
    else:
        # Find a random image from bing if not
        # provided by the user.
        print('Fetching a random image for "{}" from bing'.format(item_name))
        new_image_file_path = bbid.fetch_random_image_from_keyword(item_name)
        if new_image_file_path:
            item_img_content = open(new_image_file_path, 'rb')
        else:
            print('Could not find bing image. Using default image.')
            item_img_content = open('static/images/no-logo.gif', 'rb')

    # Create a new Item and save it in the database.
    new_item = Item(name=item_name, category=item_cat, description=item_desc, image=item_img_content.read())
    session.add(new_item)
    session.commit()

    # Remove temp directory created for bing image
    if os.path.exists('bing'):
        shutil.rmtree('bing')

    flash('New item "{}" added successfully'.format(item_name))

    return redirect(url_for('login'))


@app.route('/gconnect', methods=['POST'])
def gconnect():
    # Validate state token
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state parameter.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    if not request.headers.get('X-Requested-With'):
        response = make_response(json.dumps('Invalid headers'), 403)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Obtain authorization code
    auth_code = request.data

    credentials = client.credentials_from_clientsecrets_and_code(
        CLIENT_SECRETS_FILE,
        ['openid', 'profile', 'email'],
        auth_code)


    # Store the access token in the session for later use.
    login_session['access_token'] = credentials.access_token
    login_session['userid'] = credentials.id_token['sub']
    login_session['email'] = credentials.id_token['email']
    login_session['picture'] = credentials.id_token['picture']

    print('username : ', login_session['userid'])
    print('picture  : ', login_session['picture'])
    print('email    : ', login_session['email'])

    output = ''
    output += '<h1>Welcome, '
    output += login_session['userid']
    output += '!</h1>'
    output += '<img src="'
    output += login_session['picture']
    output += ' " style = "width: 300px; height: 300px;border-radius: ' \
              '150px;-webkit-border-radius: 150px;-moz-border-radius: 150px;"> '
    flash("you are now logged in as %s" % login_session['userid'])
    return output


if __name__ == '__main__':
    app.secret_key = 'super_secret_key'
    app.debug = True
    app.run(host='0.0.0.0', port=5001)
