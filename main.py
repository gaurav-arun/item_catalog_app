import datetime
import json
import os
import pathlib
import time
import urllib

import requests
from flask import Flask, render_template, request, redirect, url_for, flash
from flask import make_response
from flask import session as login_session
from oauth2client.client import FlowExchangeError
from oauth2client.client import flow_from_clientsecrets
from sqlalchemy import create_engine, desc, func
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm.exc import NoResultFound

import utils
from bbid import bbid
from database_setup import Base, User, Item

app = Flask(__name__)

APPLICATION_NAME = "Item Catalog Application"

GOOGLE_CLIENT_SECRETS_FILE = 'client_secrets.json'
GOOGLE_CLIENT_ID = json.loads(open(GOOGLE_CLIENT_SECRETS_FILE, 'r').read())['web']['client_id']

FB_CLIENT_SECRETS_FILE = 'fb_client_secrets.json'
FB_APP_ID = json.loads(open(FB_CLIENT_SECRETS_FILE, 'r').read())['app_id']
FB_APP_SECRET = json.loads(open(FB_CLIENT_SECRETS_FILE, 'r').read())['app_secret']

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


def _make_response(msg, error_code):
    res = make_response(json.dumps(msg), error_code)
    res.headers['Content-Type'] = 'application/json'
    return res


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
    user_id = get_userid(login_session["email"])
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

    return _make_response('Item deleted successfully', 200)


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
    # Category is stored in lowercase letters only.
    category = category.lower()
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
        return _make_response('Invalid state parameter', 401)

    try:
        # Upgrade the authorization code into a credentials object
        oauth_flow = flow_from_clientsecrets('client_secrets.json', scope='')
        oauth_flow.redirect_uri = 'postmessage'
        credentials = oauth_flow.step2_exchange(request.data)
    except FlowExchangeError:
        return _make_response('Failed to upgrade the authorization code', 401)

    # Check that the access token is valid.
    access_token = credentials.access_token

    url = ('https://www.googleapis.com/oauth2/v2/tokeninfo?access_token={}'.format(access_token))
    result = requests.get(url)
    # If there was an error in the access token info, abort.
    if result.status_code != 200:
        return _make_response('Failed to authorize with google server', 500)

    result_json = result.json()
    # Verify that the access token is used for the intended user.
    google_id = credentials.id_token['sub']
    if result_json['user_id'] != google_id:
        return _make_response('Failed to validate user id', 401)

    # Verify that the access token is valid for this app.
    if result_json['issued_to'] != GOOGLE_CLIENT_ID:
        return _make_response('Failed to validate client id', 401)

    stored_access_token = login_session.get('access_token')
    stored_google_id = login_session.get('google_id')
    if stored_access_token is not None and google_id == stored_google_id:
        return _make_response('User is already connected.', 200)

    # Store the access token in the session for later use.
    login_session['access_token'] = credentials.access_token
    login_session['google_id'] = google_id

    # Get user info
    userinfo_url = "https://www.googleapis.com/oauth2/v2/userinfo"
    params = {
        'access_token': credentials.access_token,
        'alt': 'json'
    }

    res = requests.get(userinfo_url, params=params)
    res_json = res.json()

    login_session['username'] = res_json['name']
    login_session['picture'] = res_json['picture']
    login_session['email'] = res_json['email']
    # ADD PROVIDER TO LOGIN SESSION
    login_session['provider'] = 'google'

    # see if user exists, if it doesn't make a new one
    user_id = get_userid(res_json["email"])
    if not user_id:
        user_id = create_user()
    login_session['user_id'] = user_id

    return _make_response('Google login successful', 200)


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
        return _make_response('User is not connected', 401)

    url = 'https://accounts.google.com/o/oauth2/revoke?token={}'.format(access_token)
    result = requests.get(url)
    if result.status_code != '200':
        return _make_response('Failed to disconnect from google.', 400)

    return _make_response('User disconnected from google.', 200)


@app.route('/fbconnect', methods=['POST'])
def fbconnect():
    if request.args.get('state') != login_session['state']:
        return _make_response('Invalid state parameter', 401)

    client_token = request.data.decode('ascii')
    print("Client token received {}".format(client_token))

    url = 'https://graph.facebook.com/oauth/access_token?grant_type=fb_exchange_token&' \
          'client_id={}&client_secret={}&fb_exchange_token={}'.format(FB_APP_ID,
                                                                      FB_APP_SECRET,
                                                                      client_token)
    result = requests.get(url).json()
    access_token = result['access_token']

    # Use token to get user info from API
    url = 'https://graph.facebook.com/v4.0/me?access_token={}&fields=name,id,email'.format(access_token)
    result = requests.get(url)

    result_json = result.json()
    login_session['provider'] = 'facebook'
    login_session['username'] = result_json["name"]
    login_session['email'] = result_json["email"]
    login_session['facebook_id'] = result_json["id"]

    # The token must be stored in the login_session in order to properly logout
    login_session['access_token'] = access_token

    # Get user picture
    url = 'https://graph.facebook.com/v4.0/me/picture?access_token={}&redirect=0&height=200&width=200'.format(
        client_token)
    result = requests.get(url)
    result_json = result.json()
    login_session['picture'] = result_json["data"]["url"]

    # see if user exists
    user_id = get_userid(login_session['email'])
    if not user_id:
        user_id = create_user()
    login_session['user_id'] = user_id

    return _make_response('Facebook login successful', 200)


@app.route('/fbdisconnect')
def fbdisconnect():
    facebook_id = login_session['facebook_id']
    # The access token must me included to successfully logout
    access_token = login_session['access_token']
    url = 'https://graph.facebook.com/{}/permissions?access_token={}'.format(facebook_id, access_token)
    result = requests.delete(url)
    if result.status_code != 200:
        return _make_response('Failed to disconnect from facebook', 401)

    return _make_response('Facebook logout successful', 200)


# Disconnect based on provider
@app.route('/disconnect')
def disconnect():
    if 'provider' in login_session:
        if login_session['provider'] == 'google':
            gdisconnect()
            del login_session['google_id']
            del login_session['access_token']
        elif login_session['provider'] == 'facebook':
            fbdisconnect()
            del login_session['facebook_id']

        del login_session['username']
        del login_session['email']
        del login_session['picture']
        del login_session['user_id']
        del login_session['provider']

    return _make_response('Logout successful', 200)


def create_user():
    new_user = User(name=login_session['username'], email=login_session[
        'email'], picture=login_session['picture'])
    session.add(new_user)
    session.commit()
    user = session.query(User).filter_by(email=login_session['email']).one()
    return user.id


def get_userid(email):
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
