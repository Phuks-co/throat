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
                    document.location.reload();
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

    $("#edit-user-form").submit(function(e) {
        $("#edituser-btnsubmit").prop('disabled', true);
        $("#edituser-btnsubmit").text('editing user info...');
        $.ajax({
            type: "POST",
            url: '/do/edit_user/'+ $("#edit-user-form").data('user'), // XXX: Hardcoded URL because this is supposed to be a static file
            data: $("#edit-user-form").serialize(),
            dataType: 'json',
            success: function(data) {
                if (data.status != "ok") {
                    checkErrors(data, "edit-user-form");
                } else {
                    $("#edit-user-form").html("<h1>User edited!</h1>You can now <a href=\"" + data.addr + "\">visit your profile</a>.")
                }
                $("#edituser-btnsubmit").prop('disabled', false);
                $("#edituser-btnsubmit").text('Edit user info');
            },
            error: function(data, err) {
                $("#edit-user-form .div-error p").html("<ul><li>Error while contacting the server</li></ul>");
                $("#edit-user-form .div-error").show();
                $("#edituser-btnsubmit").prop('disabled', false);
                $("#edituser-btnsubmit").text('Edit user info');
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
                    $("#login-btnsubmit").prop('disabled', false);
                    $("#login-btnsubmit").text('Login');
                } else {
                    document.location.reload();
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

    $("#edit-sub-form").submit(function(e) {
        $("#edit-sub-btnsubmit").prop('disabled', true);
        $("#edit-sub-btnsubmit").text('Editing sub info...');
        $.ajax({
            type: "POST",
            url: '/do/edit_sub/'+ $("#edit-sub-form").data('sub'), // XXX: Hardcoded URL because this is supposed to be a static file
            data: $("#edit-sub-form").serialize(),
            dataType: 'json',
            success: function(data) {
                if (data.status != "ok") {
                    checkErrors(data, "edit-sub-form");
                } else {
                    $("#edit-sub-form").html("<h1>Sub edited!</h1>You can now <a href=\"" + data.addr + "\">visit it</a>.")
                }
                $("#editsub-btnsubmit").prop('disabled', false);
                $("#editsub-btnsubmit").text('Edit sub');
            },
            error: function(data, err) {
                $("#edit-sub-form .div-error p").html("<ul><li>Error while contacting the server</li></ul>");
                $("#edit-sub-form .div-error").show();
                $("#editsub-btnsubmit").prop('disabled', false);
                $("#editsub-btnsubmit").text('Edit sub');
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

    $("#edit-txtpost-form").submit(function(e) {
        $("#edit-txpost-btnsubmit").prop('disabled', true);
        $("#edit-txpost-btnsubmit").text('Editing your post...');
        $.ajax({
            type: "POST",
            url: '/do/edit_txtpost/' + $("#edit-txtpost-form").data('sub') + '/' + $("#edit-txtpost-form").data('pid'), // XXX: Hardcoded URL because this is supposed to be a static file
            data: $("#edit-txtpost-form").serialize(),
            dataType: 'json',
            success: function(data) {
                if (data.status != "ok") {
                    checkErrors(data, "edit-txtpost-form");
                } else {
                    document.location = '/s/' + data.sub + '/' + data.pid;
                }
                $("#edit-txpost-btnsubmit").prop('disabled', false);
                $("#edit-txpost-btnsubmit").text('Edit post');
            },
            error: function(data, err) {
                $("#edit-txtpost-form .div-error p").html("<ul><li>Error while contacting the server</li></ul>");
                $("#edit-txtpost-form .div-error").show();
                $("#edit-txpost-btnsubmit").prop('disabled', false);
                $("#edit-txpost-btnsubmit").text('Edit post');
            }
        });
        e.preventDefault();
    });

    $("#link-post-form").submit(function(e) {
        $("#lnkpost-btnsubmit").prop('disabled', true);
        $("#lnkpost-btnsubmit").text('Sending your link...');
        $.ajax({
            type: "POST",
            url: '/do/lnkpost/' + $("#link-post-form").data('sub'), // XXX: Hardcoded URL because this is supposed to be a static file
            data: $("#link-post-form").serialize(),
            dataType: 'json',
            success: function(data) {
                if (data.status != "ok") {
                    checkErrors(data, "link-post-form");
                } else {
                    document.location = '/s/' + data.sub + '/' + data.pid;
                }
                $("#lnkpost-btnsubmit").prop('disabled', false);
                $("#lnkpost-btnsubmit").text('Submit link');
            },
            error: function(data, err) {
                $("#link-post-form .div-error p").html("<ul><li>Error while contacting the server</li></ul>");
                $("#link-post-form .div-error").show();
                $("#lnkpost-btnsubmit").prop('disabled', false);
                $("#lnkpost-btnsubmit").text('Submit link');
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

    $("#delete-post-form").submit(function(e) {
        $("#delpost-btnsubmit").prop('disabled', true);
        $("#delpost-btnsubmit").text('Deleting...');
        $.ajax({
            type: "POST",
            url: '/do/delete_post', // XXX: Hardcoded URL because this is supposed to be a static file
            data: $("#delete-post-form").serialize(),
            dataType: 'json',
            success: function(data) {
                if (data.status != "ok") {
                    checkErrors(data, "delete-post-form");
                } else {
                    document.location.reload();
                }
                $("#delpost-btnsubmit").prop('disabled', false);
                $("#delpost-btnsubmit").text('Delete!');
            },
            error: function(data, err) {
                $("#delete-post-form .div-error p").html("<ul><li>Error while contacting the server</li></ul>");
                $("#delete-post-form .div-error").show();
                $("#delpost-btnsubmit").prop('disabled', false);
                $("#delpost-btnsubmit").text('Submit message');
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
              document.location.reload();
            }
          },
          error: function(data, err) {
              $(e.target[e.target.length -1]).text("Submit comment.");
              $(e.target[e.target.length -1]).prop('disabled', false);
          }
        });
      e.preventDefault();
    });
    $('.delpost').click(function(e){
      $("#post").prop('value', $(e.target).data('post'));
    });
    $("#toggledark").click(function() {
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
      // Here we append it _next_ to the div that is holding the reply button
      $(e.target).parent().parent().after().after().append(x);
      // Here we hackishly get the textarea and initialize the MDE
      var l = new SimpleMDE({element: $(x[0]).children('.CommentContent').children('#comment')[0], autoDownloadFontAwesome: false, spellChecker: false, autosave: {enabled: true, unique_id: "createcomment",}});
      //$(e.target).parent().next().insertBefore('<span class="close">×</span>');

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
        $(this).parent().prev().show();
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
    $('a.btn.edit-txtpost-form').magnificPopup(mpSettings);
    $('a.btn.delpost').magnificPopup(mpSettings);

    $('.upvote').click(function(e){
      var pid = $(e.currentTarget).parent().parent().data().pid
      $.ajax({
        type: "POST",
        url: '/do/upvote/' + pid,
        dataType: 'json',
        success: function(data) {
          if(data.status == "ok"){
            $(e.currentTarget).addClass('upvoted');
            $(e.currentTarget).parent().children('.downvote').removeClass('downvoted');
            var count = $(e.currentTarget).parent().children('.count');
            count.text(parseInt(count.text())+1);
          }
        }
      });
    });

    $('.downvote').click(function(e){
      var pid = $(e.currentTarget).parent().parent().data().pid
      $.ajax({
        type: "POST",
        url: '/do/downvote/' + pid,
        dataType: 'json',
        success: function(data) {
          if(data.status == "ok"){
            $(e.currentTarget).addClass('downvoted');
            $(e.currentTarget).parent().children('.upvote').removeClass('upvoted');
            var count = $(e.currentTarget).parent().children('.count');
            count.text(parseInt(count.text())-1);
          }
        }
      });
    });

    $('.unread').click(function(e){
      var mid = $(e.currentTarget).data().mid
      $.ajax({
        type: "POST",
        url: '/do/read_pm/' + mid,
        dataType: 'json',
        success: function(data) {
          if(data.status == "ok"){
            $(e.currentTarget).addClass('read').removeClass('unread').removeClass('btn-blue');
            $(e.currentTarget).text('read')
          }
        }
      });
    });

    $('#youtubevid').click(function(e){
      var pid = $(e.currentTarget).data().pid
      var url = $(e.currentTarget).data().vid
      var frame = document.createElement('iframe');
      var vid_id = '';
      url = url.replace(/(>|<)/gi,'').split(/(vi\/|v=|\/v\/|youtu\.be\/|\/embed\/)/);
      if(url[2] !== undefined) {
        vid_id = url[2].split(/[^0-9a-z_\-]/i);
        vid_id = vid_id[0];
      }
      else {
        vid_id = url;
      }
      if($(this).hasClass('closedvid'))  {
        frame.width = '480px';
        frame.height = '320px';
        frame.style = 'display:block;'
        frame.src = 'https://www.youtube.com/embed/' + vid_id;
        playerid = 'player' + pid;
        $(e.currentTarget).addClass('openedvid').removeClass('closedvid');
        document.getElementById(playerid).appendChild(frame);
        $('#' + playerid + ' a').html('<i class="fa fa-close" aria-hidden="true"></i>');
      }
      else {
        $(this).addClass('closedvid').removeClass('openedvid');
        $('#' + playerid + ' iframe').remove()
        $('#' + playerid + ' a').html('<i class="fa fa-youtube-play" aria-hidden="true"></i>');

      }
    });

    $('#vimeovid').click(function(e){
      var pid = $(e.currentTarget).data().pid
      var url = $(e.currentTarget).data().vid
      var frame = document.createElement('iframe');
      if($(this).hasClass('closedvid'))  {
        frame.width = '480px';
        frame.height = '320px';
        frame.style = 'display:block;'
        frame.src = 'https://player.vimeo.com/video/' + vimeoID(url);
        playerid = 'player' + pid;
        $(e.currentTarget).addClass('openedvid').removeClass('closedvid');
        document.getElementById(playerid).appendChild(frame);
        $('#' + playerid + ' a').html('<i class="fa fa-close" aria-hidden="true"></i>');
      }
      else {
        $(this).addClass('closedvid').removeClass('openedvid');
        $('#' + playerid + ' iframe').remove()
        $('#' + playerid + ' a').html('<i class="fa fa-vimeo" aria-hidden="true"></i>');

      }
    });

    $('#openimg').click(function(e){
      var pid = $(e.currentTarget).data().pid
      var url = $(e.currentTarget).data().img
      var img = document.createElement('img');
      playerid = 'player' + pid;
      if($(this).hasClass('closedimg'))  {
        img.style = 'max-width:560px;display:block;';
        img.src = url;

        $(e.currentTarget).addClass('openedimg').removeClass('closedimg');
        document.getElementById(playerid).appendChild(img);
        $('#' + playerid + ' a').html('<i class="fa fa-close" aria-hidden="true"></i>');
      }
      else {
        $(this).addClass('closedimg').removeClass('openedimg');
        $('#' + playerid + ' img').remove()
        $('#' + playerid + ' a').html('<i class="fa fa-image" aria-hidden="true"></i>');
      }
    });
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

function vimeoID(url) {
  var match = url.match(/https?:\/\/(?:www\.)?vimeo.com\/(?:channels\/(?:\w+\/)?|groups\/([^\/]*)\/videos\/|album\/(\d+)\/video\/|)(\d+)(?:$|\/|\?)/);
  if (match){
    return match[3];
	}
}
