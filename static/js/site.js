// sitewide js.
$(document).ready(function () {
    $("#register-form").submit(function (e) {
        $("#reg-btnsubmit").prop('disabled', true);
        $("#reg-btnsubmit").text('Registering...');

        $.ajax({
           type: "POST",
           url: '/do/register', // XXX: Hardcoded URL because this is supposed to be a static file
           data: $("#register-form").serialize(),
           dataType: 'json',
           success: function(data){
                if(data.status != "ok"){
                    var obj = data.error,
                        ul = $("<ul>");
                    for (var i = 0, l = obj.length; i < l; ++i) {
                        ul.append("<li>" + obj[i] + "</li>");
                    }
                    $("#reg-errors").html(ul);
                    $("#div-errors").show();
                }else{ // success
                    $('a.btn.register').magnificPopup('close');
                    $('#login-intro').text("Thanks for registering! Now you can proceed to log in.");
                    $('a.btn.login').magnificPopup('open');
                }
           },
           error: function(data, err){
               $("#reg-errors").append("<ul><li>Error while contacting the server</li></ul>");
           }
        });
        e.preventDefault();
        $("#reg-btnsubmit").prop('disabled', false);
        $("#reg-btnsubmit").text('Register');

    });

    var mpSettings = {
		type: 'inline',
		preloader: false,
		focus: '#username',

		// When elemened is focused, some mobile browsers in some cases zoom in
		// It looks not nice, so we disable it:
		callbacks: {
			beforeOpen: function() {
				if($(window).width() < 700) {
					this.st.focus = false;
				} else {
					this.st.focus = '#username';
				}
			}
		}
	};
    $('a.btn.register').magnificPopup(mpSettings);
    $('a.btn.login').magnificPopup(mpSettings);
});
