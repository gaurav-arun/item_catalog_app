from sqlalchemy import create_engine, asc
from sqlalchemy.orm import sessionmaker
from database_setup import Base, User, Item
import random
from bbid import bbid
import time

# Connect to the database and create database session
engine = create_engine('sqlite:///db/itemcatalog.db', connect_args={'check_same_thread': False})
Base.metadata.bind = engine

Base.metadata.drop_all(engine)
Base.metadata.create_all(engine)

DBSession = sessionmaker(bind=engine)
session = DBSession()

items_list = {
    'Stationary': [
        'Blue Pen',
        'Notepad',
        'Ink',
        'Paintbrush',
        'Red Pen',
        'Green Pen',
        'Pencil'],
    'Wild Animal': [
        'Tiger',
        'Lion',
        'Deer',
        'Hippopotamus',
        'Wolf',
        'Python',
        'Bear',
        'Zebra',
        'Giraffe',
        'Crocodile'],
    'Birds': [
        'Blue Jay',
        'Parrot',
        'Eagle',
        'Sparrow',
        'Ostrich',
        'Hen',
        'Peacock'],
    'Household': [
        'Watch',
        'Mobile Phone',
        'Laptop',
        'Study Table',
        'Coffee Mug',
        'Alexa'
    ]
}


def bootstrap():
    user1 = User(name='Gaurav Rathore',
                 email='grathore07@gmail.com',
                 picture='https://lh5.googleusercontent.com/-iD7vfKDzZ1c/AAAAAAAAAAI/AAAAAAAAB7M/QKn9mgsvqVQ/photo.jpg')

    session.add(user1)
    session.commit()

    user2 = User(name='Gaurav Rathore',
                 email='ga_rathore07@yahoo.in',
                 picture='https://platform-lookaside.fbsbx.com/platform/profilepic/?'
                         'asid=10211941360887732&height=200&width=200&ext=1568031179&hash=AeSW6XmrvjqWW7-Q')

    session.add(user2)
    session.commit()

    user_ids = session.query(User.id).all()
    total_items = 0
    for category, items in items_list.items():
        total_items += len(items)

    remaining_items = total_items
    all_items_start = time.time()
    print('Adding {} items to the database.'.format(total_items))

    for category, items in items_list.items():
        for item in items:
            item_start = time.time()
            user_id = random.choice(user_ids)[0]
            # Find a random image from bing if not
            # provided by the user.
            print('Fetching a random image for "{}" from bing'.format(item))
            new_image_file_path = bbid.fetch_random_image_from_keyword(item)
            if new_image_file_path:
                item_img_content = open(new_image_file_path, 'rb')
            else:
                print('Could not find bing image. Using default image.')
                item_img_content = open('static/images/no-logo.gif', 'rb')

            item_obj = Item(name=item,
                            category=category,
                            description=item + " belongs to " + category + " category.",
                            image=item_img_content.read(),
                            user_id=user_id)

            session.add(item_obj)
            session.commit()
            remaining_items -= 1
            item_end = time.time()
            print('{:10} : {:5} sec, {:3} items remaining...'.format(item,
                                                                     item_end - item_start,
                                                                     remaining_items))
    all_items_end = time.time()
    print('\nAdded all items in {} seconds.'.format(all_items_end - all_items_start))
    print('\nAverage time per item is {} seconds.'.format((all_items_end - all_items_start) / total_items))


if __name__ == '__main__':
    bootstrap()
