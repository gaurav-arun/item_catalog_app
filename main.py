from flask import Flask, render_template, request, redirect, jsonify, url_for, flash
from flask import session as login_session
from flask_uploads import UploadSet, configure_uploads, IMAGES

from sqlalchemy import create_engine, desc, func
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.orm import sessionmaker
from database_setup import Base, User, Item
from bbid import bbid
import os
import pathlib
import shutil
import utils
import urllib
import time
import datetime

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

RANDOM_IMAGE_DIR = 'static/images/bing/'


@app.route('/')
@app.route('/login/')
def login():
    state = utils.get_random_state()
    login_session['state'] = state
    # Get all categories and their item count
    all_categories = session.query(Item.category, func.count(Item.category)).group_by(Item.category).all()
    # Get 10 most recently added items
    default_category = 'latest'
    latest_items = session.query(Item).order_by(desc(Item.last_updated_on)).limit(10)

    return render_template('index.html',
                           STATE=login_session['state'],
                           LOGIN_SESSION=login_session,
                           ACTIVE_CATEGORY=default_category,
                           ALL_CATEGORIES=all_categories,
                           CATEGORY_ITEMS=latest_items)


@app.route('/login_success')
def login_success():
    # Get all categories and their item count
    all_categories = session.query(Item.category, func.count(Item.category)).group_by(Item.category).all()
    # Get 10 most recently added items
    default_category = 'latest'
    latest_items = session.query(Item).order_by(desc(Item.last_updated_on)).limit(10)

    return render_template('index.html',
                           STATE=login_session['state'],
                           LOGIN_SESSION=login_session,
                           ACTIVE_CATEGORY=default_category,
                           ALL_CATEGORIES=all_categories,
                           CATEGORY_ITEMS=latest_items)


def success_response(msg):
    response = make_response(json.dumps(msg), 200)
    response.headers['Content-Type'] = 'application/json'
    return response


@app.route('/add-item', methods=['POST'])
def add_item():
    if 'username' not in login_session:
        return redirect('/login')

    # TODO: Validate user input
    item_img = request.files['item_img']
    item_name = request.form['item_name']
    item_cat = request.form['item_cat']
    item_desc = request.form['item_desc']

    if not item_name or not item_cat or not item_desc:
        print('One or more field(s) are empty!')
        return redirect(url_for('login'))

    # Url is updated below as necessary
    item_img_url = 'images/default/no-logo.gif'
    feeling_lucky = request.form.getlist('feeling-lucky-check')
    print("Is Feeling Lucky? ", feeling_lucky)

    if item_img:
        # Create new upload directory if necessary
        upload_dir = pathlib.Path('static/images/uploads')
        print("upload dir:", upload_dir)
        if not upload_dir.exists():
            upload_dir.mkdir(parents=True)

        # Save the image with timestamp(for unique filename) to images/uploads directory
        encoded_file_name = urllib.parse.quote(item_img.filename)
        last_dot_index = encoded_file_name.rfind('.')
        item_image_file_name = encoded_file_name[:last_dot_index] + '_' + \
                               str(int(time.time())) + encoded_file_name[last_dot_index:]
        item_image_file_path = upload_dir / item_image_file_name
        print("image path :", item_image_file_path)

        with open(str(item_image_file_path), 'wb') as f:
            f.write(item_img.read())

        # Create the url to be stored in DB
        item_img_url = str(item_image_file_path)[7:]
    elif feeling_lucky:
        # Find a random image from bing if user is feeling lucky!
        print('Fetching a random image for "{}" from bing'.format(item_name))
        new_image_file_path = bbid.fetch_random_image_from_keyword(item_name, output_dir=RANDOM_IMAGE_DIR)
        if new_image_file_path:
            item_img_url = new_image_file_path[7:]
        else:
            print('Could not find bing image. Using default image.')

    # Create a new Item and save it in the database.
    user_id = getUserID(login_session["email"])
    new_item = Item(name=item_name,
                    category=item_cat.lower(),
                    description=item_desc,
                    image=item_img_url,
                    user_id=user_id)
    session.add(new_item)
    session.commit()

    flash('New item "{}" added successfully'.format(item_name))

    return redirect(url_for('get_category', category=item_cat))


@app.route('/delete-item/<string:item_id>', methods=['DELETE'])
def delete_item(item_id):
    # Check if user is logged in
    if 'username' not in login_session:
        print('User not logged in')
        return redirect(url_for('login'))

    # Check if item belongs to the user
    try:
        item_to_delete = session.query(Item).filter_by(id=item_id).one()
    except NoResultFound:
        print('No matching item found in the DB.')
        return redirect(url_for('login'))

    if item_to_delete.user_id != login_session['user_id']:
        print('Item cannot be deleted by this user')
        return redirect(url_for('login'))

    # Delete item image if it is not the default image
    item_image_path = pathlib.Path('static/' + item_to_delete.image)
    if item_image_path.exists() and item_image_path.parts[-2] != 'default':
        print('Deleting item image at :', item_image_path)
        os.remove(str(item_image_path))

    # Delete item from database
    session.delete(item_to_delete)
    session.commit()
    print('Deleted item : {} with id {}'.format(item_to_delete.name, item_to_delete.id))

    return success_response('Item deleted successfully')


@app.route('/update-item/<string:item_id>', methods=['POST'])
def update_item(item_id):
    # Check if user is logged in
    if 'username' not in login_session:
        print('User not logged in')
        return redirect(url_for('login'))

    # Check if item exists in the database.
    try:
        item_to_update = session.query(Item).filter_by(id=item_id).one()
    except NoResultFound:
        print('No matching item found in the DB.')
        return redirect(url_for('login'))

    # Check if item belongs to the user
    if item_to_update.user_id != login_session['user_id']:
        print('Item cannot be updated by this user')
        return redirect(url_for('login'))

    item_img = request.files['item_img']
    item_name = request.form['item_name']
    item_cat = request.form['item_cat']
    item_desc = request.form['item_desc']

    # Url is updated below as necessary
    item_img_url = item_to_update.image
    feeling_lucky = request.form.getlist('feeling-lucky-check')
    print("Is Feeling Lucky ? ", feeling_lucky)

    if item_img:
        # Create new upload directory if necessary
        upload_dir = pathlib.Path('static/images/uploads')
        print("upload dir:", upload_dir)
        if not upload_dir.exists():
            upload_dir.mkdir(parents=True)

        # Save the image with timestamp(for unique filename) to 'images/uploads/' directory
        encoded_file_name = urllib.parse.quote(item_img.filename)
        last_dot_index = encoded_file_name.rfind('.')
        item_image_file_name = encoded_file_name[:last_dot_index] + '_' + \
                               str(int(time.time())) + encoded_file_name[last_dot_index:]
        item_image_file_path = upload_dir / item_image_file_name
        print("image path :", item_image_file_path)

        with open(str(item_image_file_path), 'wb') as f:
            f.write(item_img.read())

        # Create the url to be stored in DB
        item_img_url = str(item_image_file_path)[7:]
    elif feeling_lucky:
        # Find a random image from bing if user is feeling lucky
        print('Fetching a random image for "{}" from bing'.format(item_name))
        new_image_file_path = bbid.fetch_random_image_from_keyword(item_name, output_dir=RANDOM_IMAGE_DIR)
        if new_image_file_path:
            item_img_url = new_image_file_path[7:]
        else:
            print('Could not find bing image. Keeping original image.')

    # Delete old item image if a new image is available
    if item_img_url != item_to_update.image:
        item_image_path = pathlib.Path('static/' + item_to_update.image)
        if item_image_path.exists() and item_image_path.parts[-2] != 'default':
            print('Deleting old item image at :', item_image_path)
            os.remove(str(item_image_path))

    # Update item attributes
    item_to_update.image = item_img_url
    item_to_update.name = item_name
    item_to_update.category = item_cat
    item_to_update.description = item_desc
    item_to_update.last_updated_on = datetime.datetime.utcnow()

    # Update the database
    session.add(item_to_update)
    session.commit()
    print('Updated item : {} with id {}'.format(item_to_update.name, item_to_update.id))

    return redirect(url_for('get_category', category=item_to_update.category))


@app.route('/category/<string:category>')
def get_category(category):
    # Get all categories and their item count
    all_categories = session.query(Item.category, func.count(Item.category)).group_by(Item.category).all()

    default_category = 'latest'
    if category == default_category:
        # Get 10 most recently added items
        items_in_category = session.query(Item).order_by(desc(Item.last_updated_on)).limit(10)
    else:
        # Get all item rows in specified category
        items_in_category = session.query(Item).filter_by(category=category).order_by(desc(Item.last_updated_on)).all()

    # If the category does not exist
    # redirect the user to login page.
    if not items_in_category:
        print('No items found in "{}" category!'.format(category))
        return redirect(url_for('login'))

    return render_template('index.html',
                           STATE=login_session['state'],
                           LOGIN_SESSION=login_session,
                           ACTIVE_CATEGORY=category,
                           ALL_CATEGORIES=all_categories,
                           CATEGORY_ITEMS=items_in_category)


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

    return success_response('Google login successful')


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

    return success_response('Facebook login successful')


@app.route('/fbdisconnect')
def fbdisconnect():
    facebook_id = login_session['facebook_id']
    # The access token must me included to successfully logout
    access_token = login_session['access_token']
    url = 'https://graph.facebook.com/%s/permissions?access_token=%s' % (facebook_id, access_token)
    h = httplib2.Http()
    result = h.request(url, 'DELETE')[1]
    print('Facebook logout successful')
    return success_response('Facebook logout successful')


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

    return success_response('Logout successful')


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
