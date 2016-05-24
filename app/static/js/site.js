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
          $('#login-intro').addClass('alert ok');
          $('#login-intro').text("Thanks for registering! Now you can log in.");
          $('a.btn.login').magnificPopup('open');
          $("#reg-btnsubmit").prop('disabled', false);
          $("#reg-btnsubmit").text('Register');
        }
      },
      error: function(data, err){
        $("#register-form .div-error p").append("<ul><li>Error while contacting the server</li></ul>");
        $("#register-form .div-error").show();
        $("#reg-btnsubmit").prop('disabled', false);
        $("#reg-btnsubmit").text('Register');
      }
    });

    e.preventDefault();
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
          $("#csub-btnsubmit").prop('disabled', false);
          $("#csub-btnsubmit").text('Create sub');
        }else{ document.location = document.location; }
      },
      error: function(data, err){
        $("#login-form .div-error p").html("<ul><li>Error while contacting the server</li></ul>");
        $("#login-form .div-error").show();
        $("#login-btnsubmit").prop('disabled', false);
        $("#login-btnsubmit").text('Log in');
      }
    });
    e.preventDefault();
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
        $("#csub-btnsubmit").prop('disabled', false);
        $("#csub-btnsubmit").text('Create sub');
      },
      error: function(data, err){
        $("#csub-form .div-error p").html("<ul><li>Error while contacting the server</li></ul>");
        $("#csub-form .div-error").show();
        $("#csub-btnsubmit").prop('disabled', false);
        $("#csub-btnsubmit").text('Create sub');
      }
    });
    e.preventDefault();
  });

  $("#post-form").submit(function (e) {
    $("#txpost-btnsubmit").prop('disabled', true);
    $("#txpost-btnsubmit").text('Sending your post...');
    $.ajax({
      type: "POST",
      url: '/do/txtpost/' + $("#post-form").data('sub'), // XXX: Hardcoded URL because this is supposed to be a static file
      data: $("#post-form").serialize(),
      dataType: 'json',
      success: function(data){
        if(data.status != "ok"){
          checkErrors(data, "post-form");
        }else{
          document.location = '/s/' + data.sub + '/' + data.pid;
        }
        $("#txpost-btnsubmit").prop('disabled', false);
        $("#txpost-btnsubmit").text('Submit post');
      },
      error: function(data, err){
        $("#post-form .div-error p").html("<ul><li>Error while contacting the server</li></ul>");
        $("#post-form .div-error").show();
        $("#txpost-btnsubmit").prop('disabled', false);
        $("#txpost-btnsubmit").text('Submit post');
      }
    });
    e.preventDefault();
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
  $('a.btn.create-post').magnificPopup(mpSettings);
});

//dayNight cookie
function setDayMode() {
    var d = new Date();
    d.setTime(d.getTime() + (365*24*60*60*1000)); //365 days
    var expires = "expires=" + d.toGMTString();
    document.cookie = "dayNight" + "=" + "light" + "; " + expires;
    location.reload(); 
}
function setNightMode() {
    var d = new Date();
    d.setTime(d.getTime() + (365*24*60*60*1000)); //365 days
    var expires = "expires=" + d.toGMTString();
    document.cookie = "dayNight" + "=" + "dark" + "; " + expires;
    location.reload(); 
}

function getCookie(cname) {
    var name = cname + "=";
    var ca = document.cookie.split(';');
    for(var i=0; i<ca.length; i++) {
        var c = ca[i];
        while (c.charAt(0)==' ') {
            c = c.substring(1);
        }
        if (c.indexOf(name) == 0) {
            return c.substring(name.length, c.length);
        }
    }
    return "";
}

function checkMode() {
    var mode=getCookie("dayNight");
    if (mode == "dark") {
    //create <style> in head
    var style = document.createElement('style');
    style.type = 'text/css';
    style.innerHTML = 'body, header, footer, nav ul li a, .center, .post .title, .side {background: #101010;color: #fff;}';
    document.getElementsByTagName('head')[0].appendChild(style);    
    }
}
