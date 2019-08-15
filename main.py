import datetime
import json
import os
import pathlib
import time
import urllib

import requests
from flask import Flask, render_template, request, jsonify
from flask import make_response, redirect, url_for, flash
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
GOOGLE_CLIENT_ID = utils.get_google_client_id(secret_file=GOOGLE_CLIENT_SECRETS_FILE)

FB_CLIENT_SECRETS_FILE = 'fb_client_secrets.json'
FB_APP_ID = utils.get_fb_app_id(secret_file=FB_CLIENT_SECRETS_FILE)
FB_APP_SECRET = utils.get_fb_app_secret()

# Connect to the database and create database session
engine = create_engine('sqlite:///db/itemcatalog.db', connect_args={'check_same_thread': False})
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
session = DBSession()

RANDOM_IMAGE_DIR = 'static/images/bing/'
LATEST_CATEGORY = 'latest'
MAX_ITEMS_IN_LATEST_CATEGORY = 10


##################
# View functions #
##################

@app.route('/')
@app.route('/login/')
def login():
    """
    View function to render the default page to the user.
    Enables the user to login using Google or Facebook OAuth provider.
    :return:
    """
    state = utils.get_random_state()
    login_session['state'] = state

    # Get all categories and their item count
    all_categories = _get_categories()
    # Get most recently added items
    latest_items = _get_latest_category_items()
    return render_template('index.html',
                           STATE=login_session['state'],
                           LOGIN_SESSION=login_session,
                           ACTIVE_CATEGORY=LATEST_CATEGORY,
                           ALL_CATEGORIES=all_categories,
                           CATEGORY_ITEMS=latest_items)


@app.route('/add-item', methods=['POST'])
def add_item():
    """
    View function to add an item to the database.
    User must be logged in to perform this operation.
    :return:
    """
    if 'username' not in login_session:
        return redirect('/login')

    item_img = request.files['item-image']
    item_name = request.form['item-name']
    item_cat = request.form['item-category']
    item_desc = request.form['item-description']

    if not item_name or not item_cat or not item_desc:
        print('One or more field(s) are empty!')
        flash('Add action failed because one or more required field(s) are empty.', 'danger')
        return redirect(url_for('login'))

    item_img_url = _process_item_image(item_image=item_img,
                                       keyword=item_name,
                                       feeling_lucky=request.form.getlist('feeling-lucky-check'))

    # Create a new Item and save it in the database.
    user_id = _get_userid(login_session["email"])
    new_item = Item(name=item_name,
                    category=item_cat.lower(),
                    description=item_desc,
                    image=item_img_url,
                    user_id=user_id)
    session.add(new_item)
    session.commit()

    flash('Item "{}" added successfully'.format(item_name), 'success')

    return redirect(url_for('get_category', category=item_cat))


@app.route('/update-item/<string:item_id>', methods=['POST'])
def update_item(item_id):
    """
    View function to update an item.
    User must be logged in to perform this operation.
    :param item_id: id of the item being updated.
    :return:
    """
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

    # item_img is empty if user has not uploaded a new image.
    item_img = request.files['item-image']

    item_name = request.form['item-name']
    item_cat = request.form['item-category']
    item_desc = request.form['item-description']

    if not item_name or not item_cat or not item_desc:
        print('One or more field(s) are empty!')
        flash('Update action failed because one or more required field(s) are empty.', 'danger')
        return redirect(url_for('login'))

    item_img_url = _process_item_image(item_image=item_img,
                                       keyword=item_name,
                                       current_img_url=item_to_update.image,
                                       feeling_lucky=request.form.getlist('feeling-lucky-check'))

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

    # Update the timestamp too.
    item_to_update.last_updated_on = datetime.datetime.utcnow()

    # Save updated item in the database.
    session.add(item_to_update)
    session.commit()

    print('Updated item : {} with id {}'.format(item_to_update.name, item_to_update.id))

    flash('{} updated successfully.'.format(item_name), 'success')
    return redirect(url_for('get_category', category=item_to_update.category))


@app.route('/delete-item/<string:item_id>', methods=['DELETE'])
def delete_item(item_id):
    """
    View function for deleting an item from the database.
    User must be logged in to perform this operation.

    :param item_id: id of the item up for deletion.
    :return:
    """
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

    flash('Deleted {} Successfully.'.format(item_to_delete.name), 'success')
    return _make_response('Item deleted successfully', 200)


@app.route('/category/<string:category>')
def get_category(category):
    """
    View function for rendering category items.
    :param category: Category chosen by the user. Defaults to 'latest' category.
    :return:
    """
    # Category is stored in lowercase letters only.
    category = category.lower()
    # Get all categories and their item count
    all_categories = _get_categories()

    if category == LATEST_CATEGORY:
        # Get 10 most recently added items
        items_in_category = _get_latest_category_items()
    else:
        # Get all item rows in specified category
        items_in_category = _get_category_items(category=category, sort_on_column=Item.last_updated_on)

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
    """
    Helper function to log user in using Google OAuth
    :return:
    """
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
    user_id = _get_userid(res_json["email"])
    if not user_id:
        user_id = _create_user()
    login_session['user_id'] = user_id
    flash('Google login Successful', 'success')
    return _make_response('Google login successful', 200)


@app.route('/gdisconnect')
def gdisconnect():
    """
    Helper function to log user out from Google
    :return:
    """
    # Only disconnect a connected user.
    access_token = login_session.get('access_token')
    if access_token is None:
        return _make_response('User is not connected', 401)

    url = 'https://accounts.google.com/o/oauth2/revoke?token={}'.format(access_token)
    result = requests.get(url)

    if result.status_code != 200:
        return _make_response('Failed to disconnect with google.', 400)

    flash('Google Logout Successful', 'success')
    return _make_response('User disconnected from google.', 200)


@app.route('/fbconnect', methods=['POST'])
def fbconnect():
    """
    Helper function to log user in using Facebook OAuth
    :return:
    """
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
    user_id = _get_userid(login_session['email'])
    if not user_id:
        user_id = _create_user()
    login_session['user_id'] = user_id
    flash('Facebook Login Successful', 'success')
    return _make_response('Facebook login successful', 200)


@app.route('/fbdisconnect')
def fbdisconnect():
    """
    Helper function to log user out from facebook
    :return:
    """
    facebook_id = login_session['facebook_id']
    # The access token must me included to successfully logout
    access_token = login_session['access_token']
    url = 'https://graph.facebook.com/{}/permissions?access_token={}'.format(facebook_id, access_token)
    result = requests.delete(url)
    if result.status_code != 200:
        return _make_response('Failed to disconnect from facebook', 401)

    flash('Facebook Logout Successful', 'success')
    return _make_response('Facebook logout successful', 200)


# Disconnect based on provider
@app.route('/disconnect')
def disconnect():
    """
    Disconnects the user from OAuth provider and resets the session
    :return:
    """
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


#########################################
# JSON APIs to view Catalog Information #
#########################################


@app.route('/api/v1/catalog/json')
def catalog_json():
    """
    API for fetching all the items in the Item table.
    :return: All items in item table JSON.
    """
    all_items = _get_all_items()
    return jsonify(Items=[item.serialize for item in all_items], Count=len(all_items))


@app.route('/api/v1/categories/json')
def category_json():
    """
    API for fetching all categories in the Item table.
    :return: All categories and count of items as JSON.
    """
    all_categories = _get_categories()
    return jsonify(Categories={category: count for category, count in all_categories})


@app.route('/api/v1/categories/<string:category>/json')
def category_items_json(category):
    """
    API for fetching all items in the specified category.
    :param category: category for which items are requested.
    :return: All items in specified category as JSON.
    """
    category_items = _get_category_items(category, sort_on_column=Item.id)
    return jsonify(Count=len(category_items), Items=[item.serialize for item in category_items])


@app.route('/api/v1/items/<string:item_id>/json')
def item_json(item_id):
    """
    API for fetching an item with specified id
    :param item_id: id of the item
    :return: One item with matching id as JSON.
    """
    item = _get_item(item_id)
    return jsonify(Item=item.serialize) if item else jsonify({'error': 'Item not found'})


#######################################
# Request processing helper functions #
#######################################

def _make_response(msg, error_code):
    """
    Helper function to build HTTP response.
    :param msg: Message to include in the response
    :param error_code: HTTP error code
    :return: HTTP response.
    """
    res = make_response(json.dumps(msg), error_code)
    res.headers['Content-Type'] = 'application/json'
    return res


def _process_item_image(item_image, keyword, current_img_url=None, feeling_lucky=False):
    """
    Performs necessary steps to save the image file uploaded by the user.
    If user has checked "I'm feeling lucky" checkbox, and has not uploaded
    an image, bbid module (Bulk Bing Image Downloader) is used to download
    a random image for the keyword using bing image search.

    Note that bbid usually fails to find an image if keyword is unusual or gibberish.

    Sometimes bbid fails to find and image even for most common nouns. In such cases
    a default image is used.

    If user has uploaded an image as well as checked the feeling lucky checkbox,
    image uploaded by the user is retained and bing search for a random image is not
    performed.

    :param item_image: Image received in the post request.
    :param keyword: Keyword used to perform a Bing Image Search for a random image.
    :param feeling_lucky: Random image search for keyword is  performed only if
    this is set to true.
    :return: url of the image in application's context.
    """

    # Initially the image url is current image url if item already exists
    # otherwise no-logo.gif is used.
    item_img_url = current_img_url or 'images/default/no-logo.gif'
    print("Is Feeling Lucky? ", feeling_lucky)

    if item_image:
        # Create new upload directory if necessary
        upload_dir = pathlib.Path('static/images/uploads')
        print("upload dir:", upload_dir)
        if not upload_dir.exists():
            upload_dir.mkdir(parents=True)

        # Save the image with timestamp(for unique filename) to images/uploads directory
        encoded_file_name = urllib.parse.quote(item_image.filename)
        last_dot_index = encoded_file_name.rfind('.')
        item_image_file_name = encoded_file_name[:last_dot_index] + '_' + \
            str(int(time.time())) + encoded_file_name[last_dot_index:]
        item_image_file_path = upload_dir / item_image_file_name
        print("image path :", item_image_file_path)

        with open(str(item_image_file_path), 'wb') as f:
            f.write(item_image.read())

        # Create the url to be stored in DB
        item_img_url = str(item_image_file_path)[7:]
    elif feeling_lucky:
        # Find a random image from bing if user is feeling lucky!
        print('Fetching a random image for "{}" from bing'.format(keyword))
        new_image_file_path = bbid.fetch_random_image_from_keyword(keyword=keyword, output_dir=RANDOM_IMAGE_DIR)
        if new_image_file_path:
            item_img_url = new_image_file_path[7:]
        else:
            print('Could not find bing image. Using default image.')
    return item_img_url


#############################
# DB Query Helper functions #
#############################

def _create_user():
    """
    Creates a new user for the active session.
    :return: id of the newly created user.
    """
    new_user = User(name=login_session['username'], email=login_session[
        'email'], picture=login_session['picture'])
    session.add(new_user)
    session.commit()
    user = session.query(User).filter_by(email=login_session['email']).one()
    return user.id


def _get_userid(email):
    """
    Queries the database to find an user id for provided email.
    :param email: email id of the user.
    :return: user id of the first match in the Database.
    """
    print("getting user with email:", email)
    try:
        user = session.query(User).filter_by(email=email).one()
        return user.id
    except:
        return None


def _get_item(item_id):
    """
    Queries the database to find an item with specified id
    :param item_id: id of the item
    :return: first item with matching id
    """
    try:
        item = session.query(Item).filter_by(id=item_id).one()
        return item
    except:
        return None


def _get_all_items():
    """
    Queries the database to fetch all items.
    :return: A list of items.
    """
    try:
        all_items = session.query(Item).all()
        return all_items
    except:
        return None


def _get_category_items(category, sort_on_column=Item.last_updated_on):
    """
    Queries the database to fetch all the Items in the specified category.
    :param category: Category of the items.
    :param sort_on_column: Sorts the result based on specified column in Item table.
    Default is last_updated_on column.
    :return: Sorted list of Items.
    """
    try:
        items_in_category = session.query(Item).filter_by(category=category).order_by(desc(sort_on_column)).all()
        return items_in_category
    except:
        return None


def _get_latest_category_items(sort_on_column=Item.last_updated_on, limit=MAX_ITEMS_IN_LATEST_CATEGORY):
    """
    Queries the database to fetch a list of most recently added/updated items.
    :param sort_on_column: Sorts the result based on specified column in Item table.
    Default is last_updated_on column.
    :param limit: Maximum number of items to fetch.
    :return: Sorted list of most recently added/updated items.
    """
    try:
        latest_items = session.query(Item).order_by(desc(sort_on_column)).limit(limit)
        return latest_items
    except:
        return None


def _get_categories():
    """
    Queries the database to fetch a list of categories.
    :return: A list of tuple containing [(<category_name>, <count_of_items_in_category>), ...]
    """
    try:
        all_categories = session.query(Item.category, func.count(Item.category)).group_by(Item.category).all()
        return all_categories
    except:
        return None


if __name__ == '__main__':
    app.secret_key = os.getenv('SECRET_KEY', os.urandom(24))
    app.debug = True
    app.run(host='0.0.0.0', port=5001)
