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

photos = UploadSet('photos', IMAGES)

app = Flask(__name__)

APPLICATION_NAME = "Item Catalog Application"

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
    return render_template('index.html', STATE=state)


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

    # Remove temp directory created for bing image
    if os.path.exists('bing'):
        shutil.rmtree('bing')

    flash('New item "{}" added successfully'.format(item_name))
    session.commit()

    # return jsonify({
    #     'name': item_name,
    #     'category': item_cat,
    #     'description': item_desc,
    #     'image': item_img.filename
    # })
    # print(jsonify({
    #     'name': item_name,
    #     'category': item_cat,
    #     'description': item_desc,
    #     'image': item_img.filename
    # }))
    return redirect(url_for('login'))


if __name__ == '__main__':
    app.secret_key = 'super_secret_key'
    app.debug = True
    app.run(host='0.0.0.0', port=5001)
