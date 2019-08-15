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

## Setup  
#### Clone the project:  
```
git clone https://github.com/grathore07/item_catalog_app.git
```
#### Environment
This project has been tested on **Python v3.5.2**, **virtualenv v16.0.0**
1. Install virtualenv if required
```
sudo pip install virtualenv==16.0.0
```
2. Create a new virtual environment. Following command creates a virtual environment with name ```item_catalog_env``` and activates it.
```
virtualenv --python=/usr/bin/python3 item_catalog_env
source item_catalog_env/bin/activate
```  
3. Install all python packages required for running the project using requirements.txt file.
```
pip3 install -r requirements.txt
```
4. Create an environment variable `SECRET_KEY` used by the app for signing cookies. If not provided, the application uses a random string generated at runtime.
`export SECRET_KEY='your_super_secret_key';`

#### Create Google app and Credentials for Google OAuth Sign-in
1. Go to https://console.developers.google.com and create a Web Application.
2. Click on `Create Credentials` button and select OAuth client ID.
3. Select Application type as `Web Application`
4. Under Authorized JavaScript origins add `http://localhost:5001`. This app runs on port 5001 by default. If you change it, please ensure that this origin url is also updated
5. Under Authorized redirect URIs add `http://localhost:5001/login`
6. Download credentials for this Web Client by clicking on `DOWNLOAD JSON` button on top as save it in the root directory with name `client_secrets.json`.

#### Create Facebook app and Credentials for Facebook OAuth Sign-in
1- Go to https://developers.facebook.com
2- Add a new application.  
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
8. Under Valid OAuth Redirect URIs add `http://localhost:5001/`
9. Save your changes.

#### Update Web Client to use Google and Facebook Login.
1. Open `templates/base.html`.
2. Under the head section, update Google `client_id` with `client_id` from client_secrets.json for google sign-in to work.
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
3. Under the head section, update Facebook `appId` with your `app_id` from fb_client_secrets.json for facebook sign-in to work.
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

