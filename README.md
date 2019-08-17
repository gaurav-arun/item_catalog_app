# Udacity FSND Item Catalog Project
A web application to create a catalog of Items. Every item added to the catalog has following attributes:
1. `name` : A noun or a phrase.
2. `category`: Category in which item belongs.
3. `description`: Brief description.
4. `image` : An image of the item.

## Project structure

Directory  | Content
 ---- | -----------
`db` | SQLite database
`static` | Stylesheet and Images
`templates` | Jinja2 templates
`docs` | Files for documentation
`bbid`| [Bulk Bing Image Downloader](https://github.com/grathore07/Bulk-Bing-Image-downloader.git)

#### Bulk Bing Image Downloader 
`BBID` provides api for fetching random images from Bing Image Search. It is a fork of original repo [here](https://github.com/ostrolucky/Bulk-Bing-Image-downloader.git) and is used as a submodule for this project. I added one api to fetch a random image for specified keyword from Bing. This image is used as item image if user checks `I'm feeling Lucky` checkbox while adding/updating an item as explained in CatalogApp Walkthrough section.

## Setup  
#### Clone the project:  
```
git clone https://github.com/grathore07/item_catalog_app.git
```
#### Environment
This project has been tested on **Python v3.5.2**, **virtualenv v16.0.0**, **Ubuntu 16.04LTS**
1. Install virtualenv if required
```
sudo pip install virtualenv==16.0.0
```
2. Create a new virtual environment. Following command creates a virtual environment with name ```item_catalog_env``` and activates it.
```
virtualenv --python=/usr/bin/python3 item_catalog_env
source item_catalog_env/bin/activate
```  
3. Install all python packages required for running the project using `requirements.txt` file.
```
pip3 install -r requirements.txt
```
4. Create an environment variable `SECRET_KEY` which used by the app for signing cookies. If not provided, the application uses a random string generated at runtime.
```
export SECRET_KEY='your_super_secret_key';
```

#### Create Google app and Credentials for Google OAuth Sign-in
1. Go to https://console.developers.google.com and create a Web Application.
2. Click on `Create Credentials` button and select OAuth client ID.
3. Select Application type as `Web Application`.
4. Under Authorized JavaScript origins add `http://localhost:5001`. This app runs on port 5001 by default. If you change it, please ensure that this origin url is also updated.
5. Under Authorized redirect URIs add `http://localhost:5001/login`
6. Download credentials for this Web Client by clicking on `DOWNLOAD JSON` button on top and save it in the root directory with name `client_secrets.json`.

#### Create Facebook app and Credentials for Facebook OAuth Sign-in
1. Go to https://developers.facebook.com
2. Add a new application.  
3. Click on `Settings` and under `Basic` section add Site URL as `http://localhost:5001`. Save Changes.
4. Create a file named 'fb_client_secrets.json' with following content.
```
{
  "app_id": "your_app_id",
  "app_secret": "your_app_secret"
}
```
5. Update this file with `App ID` and `App Secret` found under `Basic` section of your app.
6. Place this file in the root directory of the project.
7. Click on `Facebook Login` under `Products` section and go to `Settings`.  
8. Under Valid OAuth Redirect URIs add `http://localhost:5001/`. This app runs on port 5001 by default. If you change it, please ensure that this uri is also updated.
9. Save your changes.

#### Update Web Client to use Google and Facebook Login(OPTIONAL)
This is an optional step because these fields are automatically updated by jinja.
1. Open `templates/base.html`.
2. Under the head section, update Google `client_id` with `client_id` from `client_secrets.json` for google sign-in to work.
```
function start() {
    gapi.load('auth2', function () {
        auth2 = gapi.auth2.init({
            client_id: '<your_client_id>',
            scope: 'openid email'
        });
    });
}
```
3. Under the head section, update Facebook `appId` with your `app_id` from `fb_client_secrets.json` for facebook sign-in to work.
```
window.fbAsyncInit = function () {
    FB.init({
        appId: '<your_facebook_app_id>',
        cookie: true,  // enable cookies to allow the server to access 
        // the session
        xfbml: true,  // parse social plugins on this page
        version: 'v4.0' // The Graph API version to use for the call
    });

    // Now that we've initialized the JavaScript SDK, we call 
    // FB.getLoginStatus().  
    FB.getLoginStatus(function (response) {
        statusChangeCallback(response);
    });
};
```

## Running the app
The app runs on port 5001 by default. You can change it in `main.py`.
```
python3 main.py
```

## JSON Enpoints
Catalog App supports following JSON Endpoints for retrieving data.

Url  | Description | Http Methods
 ---- | ----------- | ------------
`/api/v1/catalog/json` | Get all catalog items. | GET 
`/api/v1/categories/json` | Get all categories. | GET
`/api/v1/categories/<string:category>/json` | Get all Items under specified category. | GET
`/api/v1/items/<string:item_id>/json` | Get details of specified item. | GET

#### API Enpoint Usage Examples
Assuming CatalogApp is running on http://localhost:5001

1. Get all categories and number of items under each category.
```
curl http://localhost:5001/api/v1/categories/json
{
  "Categories": {
    "birds": 6, 
    "household": 6, 
    "pets": 1, 
    "skateboard": 2, 
    "stationary": 4, 
    "wild animal": 10
  }
}
```
2. Get details of the item with id 22.
```
curl http://localhost:5001/api/v1/items/22/json
{
  "Item": {
    "category": "wild animal", 
    "created by": {
      "id": 2, 
      "username": "Gaurav Rathore"
    }, 
    "description": "Hippopotamus belongs to Wild Animal category.", 
    "id": 22, 
    "image": "images/bing/Hippopotamus5.jpg", 
    "name": "Hippopotamus"
  }
}
```
3. Get all items under skateboard category.
```
curl http://localhost:5001/api/v1/categories/skateboard/json
{
  "Count": 2, 
  "Items": [
    {
      "category": "skateboard", 
      "created by": {
        "id": 1, 
        "username": "Gaurav Rathore"
      }, 
      "description": "The skateboard for ninjas.", 
      "id": 32, 
      "image": "images/bing/nija_raider.jpg", 
      "name": "Ninja Raider XXL"
    }, 
    {
      "category": "skateboard"
      "created by": {
        "id": 2, 
        "username": "John Doe"
      }, 
      "description": "A skateboard for the millenials.", 
      "id": 31, 
      "image": "images/uploads/vola-pro-wax-mx-901-200-g.jpg", 
      "name": "MX 200 Pro"
    }
  ]
}
```

## CatalogApp Walkthrough

1. Initially there are no items in the database and User is shown the welcome page.
![alt text](https://github.com/grathore07/item_catalog_app/blob/master/docs/db-empty.png)

2. User can login using their Google/Facebook account by clicking on `Login` button.
![alt text](https://github.com/grathore07/item_catalog_app/blob/master/docs/login-modal.png)

3. Once user is logged in, they can see `Add Item` button on navbar, their `profile picture` and `Logout` button.
![alt text](https://github.com/grathore07/item_catalog_app/blob/master/docs/logged-in.png)

4. A logged in User can add an item by clicking on `Add Item`. A modal dialog pops up and user needs to fill in the details. User has option to `Upload an image` for the item or simply check `I'm feeling lucky` checkbox to use a random image from Bing Search. Finally, user clicks on `Add` button to add the item.
![alt text](https://github.com/grathore07/item_catalog_app/blob/master/docs/add-item-filled.png)

5. A logged in User can edit an item created by them by clicking on `Edit` button. A modal dialog pops up where user can update item details. User has option to `Upload a new image` for the item or simply check `I'm feeling lucky` checkbox to use a random image from Bing Search. Finally, user clicks on `Update` button to save the updates.
![alt text](https://github.com/grathore07/item_catalog_app/blob/master/docs/edit-item.png)

6. A logged in User can delete an item created by them by clicking on `Delete` button. A modal dialog pops up for user confirmation.
![alt text](https://github.com/grathore07/item_catalog_app/blob/master/docs/delete-item.png)

7. All users are allowed to view all the items in the database. But an user is only allowed to Edit/Delete an item created by them.
![alt text](https://github.com/grathore07/item_catalog_app/blob/master/docs/logged-out.png)
![alt text](https://github.com/grathore07/item_catalog_app/blob/master/docs/logged-in-2.png)


## Reference
1. https://github.com/udacity/ud330/tree/master/Lesson4/step2
2. https://developers.google.com/identity/sign-in/web/server-side-flow
3. https://console.developers.google.com/apis/credentials/oauthclient/109303328989-
4. https://developers.facebook.com/docs/
5. https://www.w3schools.com/bootstrap4/default.asp
6. https://getbootstrap.com/docs/4.0/getting-started/introduction/
7. Image Source: IMDB, Bing Search
