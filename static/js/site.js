// sitewide js.
$(document).ready(function () {
    $("#register-form").submit(function (e) {
        $.ajax({
           type: "POST",
           url: '/do/register', // XXX: Hardcoded URL because this is supposed to be a static file
           data: $("#register-form").serialize(),
           success: function(data)
           {
               alert(data);
           }
        });
        e.preventDefault();

    });
});
