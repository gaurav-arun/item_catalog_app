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

from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import FlowExchangeError

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
engine = create_engine('sqlite:///db/itemcatalog.db', connect_args={'check_same_thread': False})
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
session = DBSession()


@app.route('/')
@app.route('/login/')
def login():
    state = utils.get_random_state()
    login_session['state'] = state
    return render_template('index.html', STATE=state, LOGIN_SESSION=login_session)


@app.route('/login_success')
def login_success():
    return render_template('index.html', STATE=login_session['state'], LOGIN_SESSION=login_session)


@app.route('/add-new-item', methods=['POST'])
def upload():
    if 'username' not in login_session:
        return redirect('/login')

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
    user_id = getUserID(login_session["email"])
    new_item = Item(name=item_name,
                    category=item_cat,
                    description=item_desc,
                    image=item_img_content.read(),
                    user_id=user_id)
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
    # Obtain authorization code
    code = request.data

    try:
        # Upgrade the authorization code into a credentials object
        oauth_flow = flow_from_clientsecrets('client_secrets.json', scope='')
        oauth_flow.redirect_uri = 'postmessage'
        credentials = oauth_flow.step2_exchange(code)
    except FlowExchangeError:
        response = make_response(
            json.dumps('Failed to upgrade the authorization code.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Check that the access token is valid.
    access_token = credentials.access_token
    # url = ('https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=%s'
    #        % access_token)
    # h = httplib2.Http()
    # result = json.loads(h.request(url, 'GET')[1])
    # # If there was an error in the access token info, abort.
    # if result.get('error') is not None:
    #     response = make_response(json.dumps(result.get('error')), 500)
    #     response.headers['Content-Type'] = 'application/json'
    #     return response

    url = ('https://www.googleapis.com/oauth2/v2/tokeninfo?access_token=%s'
           % access_token)
    result = requests.get(url)
    # If there was an error in the access token info, abort.
    if result.status_code != 200:
        response = make_response("Server side error", 500)
        response.headers['Content-Type'] = 'application/json'
        return response

    result_j = result.json()
    # Verify that the access token is used for the intended user.
    gplus_id = credentials.id_token['sub']
    if result_j['user_id'] != gplus_id:
        response = make_response(
            json.dumps("Token's user ID doesn't match given user ID."), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is valid for this app.
    if result_j['issued_to'] != CLIENT_ID:
        response = make_response(
            json.dumps("Token's client ID does not match app's."), 401)
        print("Token's client ID does not match app's.")
        response.headers['Content-Type'] = 'application/json'
        return response

    stored_access_token = login_session.get('access_token')
    stored_gplus_id = login_session.get('gplus_id')
    if stored_access_token is not None and gplus_id == stored_gplus_id:
        response = make_response(json.dumps('Current user is already connected.'),
                                 200)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Store the access token in the session for later use.
    login_session['access_token'] = credentials.access_token
    login_session['gplus_id'] = gplus_id

    # Get user info
    userinfo_url = "https://www.googleapis.com/oauth2/v2/userinfo"
    params = {'access_token': credentials.access_token, 'alt': 'json'}
    answer = requests.get(userinfo_url, params=params)

    data = answer.json()

    login_session['username'] = data['name']
    login_session['picture'] = data['picture']
    login_session['email'] = data['email']
    # ADD PROVIDER TO LOGIN SESSION
    login_session['provider'] = 'google'

    # see if user exists, if it doesn't make a new one
    user_id = getUserID(data["email"])
    if not user_id:
        user_id = createUser(login_session)
    login_session['user_id'] = user_id

    output = ''
    output += '<h1>Welcome, '
    output += login_session['username']
    output += '!</h1>'
    output += '<img src="'
    output += login_session['picture']
    output += ' " style = "width: 300px; height: 300px;border-radius: 150px;' \
              '-webkit-border-radius: 150px;-moz-border-radius: 150px;"> '
    flash("you are now logged in as %s" % login_session['username'])
    print("google login successful!")
    return render_template('login_success.html', login_session=login_session)  # redirect(url_for('login_success'))


@app.route('/gdisconnect')
def gdisconnect():
    """
    Reference : https://developers.google.com/identity/protocols/OAuth2WebServer
    # Scroll down to the bottom or search 'revoke'
    :return:
    """
    # Only disconnect a connected user.
    access_token = login_session.get('access_token')
    if access_token is None:
        response = make_response(
            json.dumps('Current user not connected.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    url = 'https://accounts.google.com/o/oauth2/revoke?token=%s' % access_token
    h = httplib2.Http()
    result = h.request(url, 'GET')[0]
    if result['status'] == '200':
        response = make_response(json.dumps('Successfully disconnected.'), 200)
        response.headers['Content-Type'] = 'application/json'
        print('Google logout successful')
        return response
    else:
        response = make_response(json.dumps('Failed to revoke token for given user.', 400))
        response.headers['Content-Type'] = 'application/json'
        return response


@app.route('/fbconnect', methods=['POST'])
def fbconnect():
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state parameter.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    access_token = request.data.decode('ascii')
    print("access token received %s " % access_token)

    app_id = json.loads(open('fb_client_secrets.json', 'r').read())['app_id']
    app_secret = json.loads(
        open('fb_client_secrets.json', 'r').read())['app_secret']
    url = 'https://graph.facebook.com/oauth/access_token?grant_type=fb_exchange_token&' \
          'client_id=%s&client_secret=%s&fb_exchange_token=%s' % (app_id, app_secret, access_token)
    # h = httplib2.Http()
    # result = h.request(url, 'GET')[1]
    result = requests.get(url).json()
    # Use token to get user info from API
    '''
        Due to the formatting for the result from the server token exchange we have to
        split the token first on commas and select the first index which gives us the key : value
        for the server access token then we split it on colons to pull out the actual token value
        and replace the remaining quotes with nothing so that it can be used directly in the graph
        api calls
    '''
    token = result['access_token']  # 'result.split(',')[0].split(':')[1].replace('"', '')

    url = 'https://graph.facebook.com/v4.0/me?access_token=%s&fields=name,id,email' % token
    result = requests.get(url)
    # h = httplib2.Http()
    # result = h.request(url, 'GET')[1]
    # print("url sent for API access:%s"% url)
    # print("API JSON result: %s" % result)

    data = result.json()
    login_session['provider'] = 'facebook'
    login_session['username'] = data["name"]
    login_session['email'] = data["email"]
    login_session['facebook_id'] = data["id"]

    # The token must be stored in the login_session in order to properly logout
    login_session['access_token'] = token

    # Get user picture
    url = 'https://graph.facebook.com/v4.0/me/picture?access_token=%s&redirect=0&height=200&width=200' % token
    result = requests.get(url)
    data = result.json()
    # h = httplib2.Http()
    # result = h.request(url, 'GET')[1]
    # data = json.loads(result)

    login_session['picture'] = data["data"]["url"]

    # see if user exists
    user_id = getUserID(login_session['email'])
    if not user_id:
        user_id = createUser(login_session)
    login_session['user_id'] = user_id

    output = ''
    output += '<h1>Welcome, '
    output += login_session['username']

    output += '!</h1>'
    output += '<img src="'
    output += login_session['picture']
    output += ' " style = "width: 300px; height: 300px;border-radius: 150px;' \
              '-webkit-border-radius: 150px;-moz-border-radius: 150px;"> '

    print("Facebook login successful!")
    return redirect(url_for('login_success'))


@app.route('/fbdisconnect')
def fbdisconnect():
    facebook_id = login_session['facebook_id']
    # The access token must me included to successfully logout
    access_token = login_session['access_token']
    url = 'https://graph.facebook.com/%s/permissions?access_token=%s' % (facebook_id, access_token)
    h = httplib2.Http()
    result = h.request(url, 'DELETE')[1]
    print('Facebook logout successful')
    return "you have been logged out"


# Disconnect based on provider
@app.route('/disconnect')
def disconnect():
    if 'provider' in login_session:
        if login_session['provider'] == 'google':
            gdisconnect()
            del login_session['gplus_id']
            del login_session['access_token']
        if login_session['provider'] == 'facebook':
            fbdisconnect()
            del login_session['facebook_id']
        del login_session['username']
        del login_session['email']
        del login_session['picture']
        del login_session['user_id']
        del login_session['provider']
        print("You have successfully been logged out.")
    else:
        print("You were not logged in")
    return render_template('index.html', STATE=login_session['state'], LOGIN_SESSION=login_session)


def createUser(login_session):
    newUser = User(name=login_session['username'], email=login_session[
        'email'], picture=login_session['picture'])
    session.add(newUser)
    session.commit()
    user = session.query(User).filter_by(email=login_session['email']).one()
    return user.id


def getUserInfo(user_id):
    user = session.query(User).filter_by(id=user_id).one()
    return user


def getUserID(email):
    print("getting user with email:", email)
    try:
        user = session.query(User).filter_by(email=email).one()
        return user.id
    except:
        return None


if __name__ == '__main__':
    app.secret_key = 'super_secret_key'
    app.debug = True
    app.run(host='0.0.0.0', port=5001)
