function HandleBrowseClick(input_image) {
    var fileinput = document.getElementById(input_image);
    fileinput.click();
}

function EditItemModalWindow(button) {
    itemId = button.dataset.editid;
    item_img_id = '#' + itemId + '_img';
    item_title_id = '#' + itemId + '_tit';
    item_cat_id = '#' + itemId + '_cat';
    item_desc_id = '#' + itemId + '_desc';
    $('#add-item-title')[0].innerText = "Edit Item"
    $('#add-item-form')[0].action = "/update-item/" + itemId
    $('#add-item-image-preview')[0].src = $(item_img_id)[0].src
    $('#add-item-tit').val($(item_title_id)[0].innerText)

    itemCatnId = $(item_cat_id)[0].innerText;
    itemCat = itemCatnId.slice(0, itemCatnId.lastIndexOf(':') - 1)
    $('#add-item-cat').val(itemCat)

    $('#add-item-desc').val($(item_desc_id)[0].innerText)
    $('#addItemModal').modal("show")
}

function resetAddItemModal() {
    $('#add-item-title')[0].innerText = "Add New Item"
    $('#add-item-form')[0].action = "{{ url_for('add_item') }}";
    $('#add-item-image-preview')[0].src = "{{ url_for('static', filename='images/default/no-logo.gif') }}";
    $('#add-item-tit').val('');
    $('#add-item-cat').val('');
    $('#add-item-desc').val('');
}

function DeleteItemModalWindow(button) {
    itemId = button.dataset.deleteid
    item_title = $('#' + itemId + '_tit')[0].innerText;
    item_cat = $('#' + itemId + '_cat')[0].innerText;
    $('#del-conf-msg')[0].innerText = "Are you sure you want to delete '" + item_title + ", " + item_cat + "'?"

    // Used to make a delete request to the server on button click.
    $('#del-item-btn')[0].dataset.deleteid = itemId

    $('#delItemModal').modal("show")
}

function resetDeleteItemModal() {
    $('#del-conf-msg')[0].innerText = ""
    $('#del-item-btn')[0].dataset.deleteid = ""
}


function handleLogin(button) {
    console.log("state:" + button.dataset.state)
    if (button.dataset.state === "login") {
        $('#loginModalForm').modal("toggle")
    }
    else {
        $.get("/disconnect", function (data, status) {
            console.log('Successfully logged out')
            window.location.href = "/login"
        });
    }

}

// Register for various modal event
function registerForModalEvents() {
    $("#addItemModal").on('hide.bs.modal', function () {
        console.log('Hide event: Clearing add item modal')
        resetAddItemModal();
    });

    $("#add-item-btn").click(function () {
        console.log('Submitting Add item form...')
        $('#add-item-form').submit()
    });

    $("#delItemModal").on('hide.bs.modal', function () {
        console.log('Hide event: Clearing delete item modal')
        resetDeleteItemModal();
    });

    $("#del-item-btn").click(function () {
        console.log('Submitting delete request : ' + this.dataset.deleteid)
        itemId = this.dataset.deleteid
        itemCatnId = $('#' + itemId + '_cat')[0].innerText;
        itemCat = itemCatnId.slice(0, itemCatnId.lastIndexOf(':') - 1)
        $.ajax({
            url: '/delete-item/' + itemId,
            type: 'DELETE',
            success: function (result) {
                console.log('Getting ' + '/category/' + itemCat)
                window.location.href = '/category/' + itemCat
            }
        });

    });
}     