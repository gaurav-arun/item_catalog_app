from flask import Flask, render_template, request, redirect, jsonify, url_for, flash
from flask import session as login_session
from flask_uploads import UploadSet, configure_uploads, IMAGES

from sqlalchemy import create_engine, asc
from sqlalchemy.orm import sessionmaker
from database_setup import Base, User, Item
import google_image_scraper

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
    item_img = request.files['item_img'].read()
    item_name = request.form['item_name']
    item_cat = request.form['item_cat']
    item_desc = request.form['item_desc']

    # Find a random image from google if not
    # provided by the user.
    if not item_img:
        item_img = google_image_scraper.get_random_image(item_name)

    new_item = Item(name=item_name, category=item_cat, description=item_desc, image=item_img)
    session.add(new_item)
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
