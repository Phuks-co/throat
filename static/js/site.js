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
