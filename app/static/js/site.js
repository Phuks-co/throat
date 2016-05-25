// sitewide js.
$(document).ready(function() {
    function checkErrors(data, div) {
        var obj = data.error,
            ul = $("<ul>");
        for (var i = 0, l = obj.length; i < l; ++i) {
            ul.append("<li>" + obj[i] + "</li>");
        }
        $("#" + div + " .div-error p").html(ul);
        $("#" + div + " .div-error").show();
    }

    $("#register-form").submit(function(e) {
        $("#reg-btnsubmit").prop('disabled', true);
        $("#reg-btnsubmit").text('Registering...');
        $.ajax({
            type: "POST",
            url: '/do/register', // XXX: Hardcoded URL because this is supposed to be a static file
            data: $("#register-form").serialize(),
            dataType: 'json',
            success: function(data) {
                if (data.status != "ok") {
                    checkErrors(data, "register-form");
                } else { // success
                    $('a.btn.register').magnificPopup('close');
                    $('#login-intro').addClass('alert ok');
                    $('#login-intro').text("Thanks for registering! Now you can log in.");
                    $('a.btn.login').magnificPopup('open');
                }
                $("#reg-btnsubmit").prop('disabled', false);
                $("#reg-btnsubmit").text('Register');
            },
            error: function(data, err) {
                $("#register-form .div-error p").append("<ul><li>Error while contacting the server</li></ul>");
                $("#register-form .div-error").show();
                $("#reg-btnsubmit").prop('disabled', false);
                $("#reg-btnsubmit").text('Register');
            }
        });

        e.preventDefault();
    });

    $("#login-form").submit(function(e) {
        $("#login-btnsubmit").prop('disabled', true);
        $("#login-btnsubmit").text('Logging in...');
        $.ajax({
            type: "POST",
            url: '/do/login', // XXX: Hardcoded URL because this is supposed to be a static file
            data: $("#login-form").serialize(),
            dataType: 'json',
            success: function(data) {
                if (data.status != "ok") {
                    checkErrors(data, "login-form");
                    $("#login-btnsubmit").prop('disabled', f);
                    $("#login-btnsubmit").text('Login');
                } else {
                    document.location = document.location;
                }
            },
            error: function(data, err) {
                $("#login-form .div-error p").html("<ul><li>Error while contacting the server</li></ul>");
                $("#login-form .div-error").show();
                $("#login-btnsubmit").prop('disabled', false);
                $("#login-btnsubmit").text('Log in');
            }
        });
        e.preventDefault();
    });

    $("#csub-form").submit(function(e) {
        $("#csub-btnsubmit").prop('disabled', true);
        $("#csub-btnsubmit").text('Creating sub...');
        $.ajax({
            type: "POST",
            url: '/do/create_sub', // XXX: Hardcoded URL because this is supposed to be a static file
            data: $("#csub-form").serialize(),
            dataType: 'json',
            success: function(data) {
                if (data.status != "ok") {
                    checkErrors(data, "csub-form");
                } else {
                    $("#csub-form").html("<h1>Sub created!</h1>You can now <a href=\"" + data.addr + "\">visit it</a>.")
                }
                $("#csub-btnsubmit").prop('disabled', false);
                $("#csub-btnsubmit").text('Create sub');
            },
            error: function(data, err) {
                $("#csub-form .div-error p").html("<ul><li>Error while contacting the server</li></ul>");
                $("#csub-form .div-error").show();
                $("#csub-btnsubmit").prop('disabled', false);
                $("#csub-btnsubmit").text('Create sub');
            }
        });
        e.preventDefault();
    });

    $("#post-form").submit(function(e) {
        $("#txpost-btnsubmit").prop('disabled', true);
        $("#txpost-btnsubmit").text('Sending your post...');
        $.ajax({
            type: "POST",
            url: '/do/txtpost/' + $("#post-form").data('sub'), // XXX: Hardcoded URL because this is supposed to be a static file
            data: $("#post-form").serialize(),
            dataType: 'json',
            success: function(data) {
                if (data.status != "ok") {
                    checkErrors(data, "post-form");
                } else {
                    document.location = '/s/' + data.sub + '/' + data.pid;
                }
                $("#txpost-btnsubmit").prop('disabled', false);
                $("#txpost-btnsubmit").text('Submit post');
            },
            error: function(data, err) {
                $("#post-form .div-error p").html("<ul><li>Error while contacting the server</li></ul>");
                $("#post-form .div-error").show();
                $("#txpost-btnsubmit").prop('disabled', false);
                $("#txpost-btnsubmit").text('Submit post');
            }
        });
        e.preventDefault();
    });

    $("#msg-form").submit(function(e) {
        $("#msg-btnsubmit").prop('disabled', true);
        $("#msg-btnsubmit").text('Sending your msg...');
        $.ajax({
            type: "POST",
            url: '/do/sendmsg/' + $("#msg-form").data('user'), // XXX: Hardcoded URL because this is supposed to be a static file
            data: $("#msg-form").serialize(),
            dataType: 'json',
            success: function(data) {
                if (data.status != "ok") {
                    checkErrors(data, "msg-form");
                } else {
                    document.location = '/messages';
                }
                $("#msg-btnsubmit").prop('disabled', false);
                $("#msg-btnsubmit").text('Submit message');
            },
            error: function(data, err) {
                $("#msg-form .div-error p").html("<ul><li>Error while contacting the server</li></ul>");
                $("#msg-form .div-error").show();
                $("#msg-btnsubmit").prop('disabled', false);
                $("#msg-btnsubmit").text('Submit message');
            }
        });
        e.preventDefault();
    });

    $(document).on('submit', ".comment-form", function(e){
      // Note for future self: This is a really fucking hacky way to do this.
      // This thing will break if the order of the fields changes >_>
      $(e.target[e.target.length -1]).text("Sending comment...")
      $(e.target[e.target.length -1]).prop('disabled', true)
      $.ajax({
          type: "POST",
          url: '/do/sendcomment/' + $(e.target[1]).prop('value') + '/' + $(e.target[2]).prop('value'),
          data: $(e.target).serialize(),
          dataType: 'json',
          success: function(data) {
            if(data.status != "ok"){
            }else{
              console.log("foo")
              document.location = document.location;
            }
          },
          error: function(data, err) {
              $(e.target[e.target.length -1]).text("Submit comment.");
              $(e.target[e.target.length -1]).prop('disabled', false);
          }
        });
      e.preventDefault();
    });

    $("#toggledark").click(function() {
        console.log("beep");
        var mode = getCookie("dayNight");
        var d = new Date();
        d.setTime(d.getTime() + (365 * 24 * 60 * 60 * 1000)); //365 days
        var expires = "expires=" + d.toGMTString();
        if (mode == "dark") {
            document.cookie = "dayNight" + "=" + "light" + "; " + expires + ";path=/";
            $("body").removeClass("dark");
        } else {
            document.cookie = "dayNight" + "=" + "dark" + "; " + expires + ";path=/";
            $("body").addClass("dark");
        }
    });

    $('.lnkreply').click(function(e) {
      // Explaining what this does because it'll be a pain in the ass to maintain

      // We have stored an additional copy of the form, without the MDE initialized.
      // Here we clone it and remove the 'display: none'
      var x = $($(".comment-form.moving")[0]).clone().show();
      $(x).append('<span class="close">×</span>');
      // Here we append it _next_ to the div that is holding the reply button
      $(e.target).parent().parent().after().append(x);
      // Here we hackishly get the textarea and initialize the MDE
      var l = new SimpleMDE({element: $(x[0]).children('.CommentContent').children('#comment')[0], autoDownloadFontAwesome: false, spellChecker: false, autosave: {enabled: true, unique_id: "createcomment",}});
      // Here we hide the reply button...
      $(e.target).parent().hide();
      // Guesswork to get the right elements..
      var parent = $(e.target).data().to;
      // And here we hackishly set the value of the 'parent' hidden input to the cid
      // of the parent comment.
      $(e.target).parent().next().children('#parent').prop('value', parent);
      e.preventDefault();
    });

    $(document).on('click', '.close', function(e) {
        $(this).parent().remove();
    });

    var mpSettings = {
        type: 'inline',
        preloader: false,
        focus: '#username',
        callbacks: {
            beforeOpen: function() {
                if ($(window).width() < 700) {
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
    $('a.btn.send-message').magnificPopup(mpSettings);
});

function getCookie(cname) {
    var name = cname + "=";
    var ca = document.cookie.split(';');
    for (var i = 0; i < ca.length; i++) {
        var c = ca[i];
        while (c.charAt(0) == ' ') {
            c = c.substring(1);
        }
        if (c.indexOf(name) == 0) {
            return c.substring(name.length, c.length);
        }
    }
    return "";
}
