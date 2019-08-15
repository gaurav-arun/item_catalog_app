function signInCallback(authResult) {
    if (authResult['code']) {

        // // Hide the sign-in button now that the user is authorized, for example:
        // $('#signinButton').attr('style', 'display: none');
        console.log('Executing Sigincallback ...')

        // Close the login modal and wait for server redirect.
        $('#loginModalForm').modal("hide")

        // Send the code to the server
        $.ajax({
            type: 'POST',
            url: '/gconnect?state={{STATE}}',
            // Always include an `X-Requested-With` header in every AJAX request,
            // to protect against CSRF attacks.
            headers: {
                'X-Requested-With': 'XMLHttpRequest'
            },
            contentType: 'application/octet-stream; charset=utf-8',
            success: function (result) {
                console.log('Successfully logged in')
                // $('#loginModalForm').modal("hide")
                // $('#loginLogoutBtn').html("<span class=\"fas fa-sign-out-alt p-1\"></span>Logout")
                // // Set the button state to logout so that when user clicks on it
                // // next time logout is triggered.
                // $('#loginLogoutBtn')[0].dataset.state = 'logout'

                window.location.href = "/login"
            },
            processData: false,
            data: authResult['code']
        });
    } else {
        console.log("Server side error.")
    }
}