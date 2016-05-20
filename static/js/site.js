// sitewide js.
$(document).ready(function () {
  function checkErrors(data, div){
    var obj = data.error,
        ul = $("<ul>");
    for (var i = 0, l = obj.length; i < l; ++i) {
        ul.append("<li>" + obj[i] + "</li>");
    }
    $("#" + div + " .div-error p").html(ul);
    $("#" + div + " .div-error").show();
  }

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
          checkErrors(data, "register-form");
        }else{ // success
          $('a.btn.register').magnificPopup('close');
          $('#login-intro').text("Thanks for registering! Now you can proceed to log in.");
          $('a.btn.login').magnificPopup('open');
        }
      },
      error: function(data, err){
        $("#register-form .div-error p").append("<ul><li>Error while contacting the server</li></ul>");
        $("#register-form .div-error").show();
      }
    });

    e.preventDefault();
    $("#reg-btnsubmit").prop('disabled', false);
    $("#reg-btnsubmit").text('Register');
  });

  $("#login-form").submit(function (e) {
    $("#login-btnsubmit").prop('disabled', true);
    $("#login-btnsubmit").text('Logging in...');
    $.ajax({
      type: "POST",
      url: '/do/login', // XXX: Hardcoded URL because this is supposed to be a static file
      data: $("#login-form").serialize(),
      dataType: 'json',
      success: function(data){
        if(data.status != "ok"){
          checkErrors(data, "login-form");
        }else{ document.location = document.location; }
      },
      error: function(data, err){
        $("#login-form .div-error p").html("<ul><li>Error while contacting the server</li></ul>");
        $("#login-form .div-error").show();
      }
    });
    e.preventDefault();
    $("#login-btnsubmit").prop('disabled', false);
    $("#login-btnsubmit").text('Register');
  });

  $("#csub-form").submit(function (e) {
    $("#csub-btnsubmit").prop('disabled', true);
    $("#csub-btnsubmit").text('Creating sub...');
    $.ajax({
      type: "POST",
      url: '/do/create_sub', // XXX: Hardcoded URL because this is supposed to be a static file
      data: $("#csub-form").serialize(),
      dataType: 'json',
      success: function(data){
        if(data.status != "ok"){
          checkErrors(data, "csub-form");
        }else{
          $("#csub-form").html("<h1>Sub created!</h1>You can now <a href=\""+ data.addr + "\">visit it</a>.")
        }
      },
      error: function(data, err){
        $("#csub-form .div-error p").html("<ul><li>Error while contacting the server</li></ul>");
        $("#csub-form .div-error").show();
      }
    });
    e.preventDefault();
    $("#login-btnsubmit").prop('disabled', false);
    $("#login-btnsubmit").text('Register');
  });


  var mpSettings = {
    type: 'inline',
		preloader: false,
		focus: '#username',
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
  $('a.btn.create-sub').magnificPopup(mpSettings);
});
