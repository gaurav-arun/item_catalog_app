 // This is called with the results from from FB.getLoginStatus().
 function statusChangeCallback(response) {
    console.log('statusChangeCallback');
    console.log(response);
    // The response object is returned with a status field that lets the
    // app know the current login status of the person.
    // Full docs on the response object can be found in the documentation
    // for FB.getLoginStatus().
    if (response.status === 'connected') {
        // Logged into your app and Facebook.
        console.log("access_token : " + response.authResponse.accessToken)
        response_token = response.authResponse.accessToken
        sendTokenToServer(response_token);
    } else {
        // The person is not logged into your app or we are unable to tell.
        console.log('The person is not logged into your app or we are unable to tell')
    }
}

// This function is called when someone finishes with the Login
// Button.  See the onlogin handler attached to it in the sample
// code below.
function checkLoginState() {
    FB.getLoginStatus(function (response) {
        statusChangeCallback(response);
    });
}


// Load the SDK asynchronously
(function (d, s, id) {
    var js, fjs = d.getElementsByTagName(s)[0];
    if (d.getElementById(id)) return;
    js = d.createElement(s); js.id = id;
    js.src = "https://connect.facebook.net/en_US/sdk.js";
    fjs.parentNode.insertBefore(js, fjs);
}(document, 'script', 'facebook-jssdk'));

// Here we run a very simple test of the Graph API after login is
// successful.  See statusChangeCallback() for when this call is made.
function sendTokenToServer(response_token) {
    console.log('Welcome!  Fetching your information.... ');

    // Close the login modal and wait for server redirect.
    $('#loginModalForm').modal("hide")

    FB.api('/me', function (response) {
        console.log('Successful login for: ' + response.name);
        $.ajax({
            type: 'POST',
            url: '/fbconnect?state={{STATE}}',
            processData: false,
            data: response_token,
            contentType: 'application/octet-stream; charset=utf-8',
            success: function (result) {
                // Handle or verify the server response if necessary.
                if (result) {
                    console.log('Login Successful!' + result + 'Redirecting...')
                    window.location.href = "/login";
                } else {
                    console.log('Failed to make a server-side call. Check your configuration and console.');
                }
            }
        });
    });
}