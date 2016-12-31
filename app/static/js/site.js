// sitewide js.
$(document).ready(function() {
  // shitless forms
  $(document).on('submit', ".ajaxform", function(e){
    e.preventDefault();
    var target = $(e.target);
    var button = $(target.find("[type=submit]")[0]);
    var btnorm = button.text();
    button.prop('disabled', true);
    button.text(button.data('prog'));
    $.ajax({
      type: "POST",
      dataType: 'json',
      url: target.prop('action'),
      data: target.serialize(),
      success: function(data) {
        if (data.status != "ok") {
          var obj = data.error,
            ul = $("<ul>"); // >_>
          for (var i = 0, l = obj.length; i < l; ++i) {
            ul.append("<li>" + obj[i] + "</li>");
          }
          target.find('.div-error').html('<span class="closebtn" onclick="this.parentElement.style.display=\'none\';">&times;</span>' +
                        '<ul>' + ul.html() + '</ul>');
          target.find('.div-error').show();
          button.text(btnorm);
          if (typeof grecaptcha != "undefined") {
              grecaptcha.reset();
          }
          button.prop('disabled', false);
        } else { // success
          target[0].reset();
          if(button.data('success')){
            button.text(button.data('success'));
          }
          if(target.data('redir')){
            if(target.data('redir') == true){
              document.location = data.addr;
            }else{
              document.location = target.data('redir');
            }
          }else if (target.data('reload')) {
            console.log('tried')
            document.location.reload();
          }else{
            button.prop('disabled', false);
          }
        }
      },
      error: function(data, err) {
        target.find('.div-error').html('<span class="closebtn" onclick="this.parentElement.style.display=\'none\';">&times;</span> <p><ul><li>Error while contacting the server</li></ul></p>');
        target.find('.div-error').show();
        button.prop('disabled', false);
        button.text(btnorm);
      }
    });
    console.log(target.data());
  });

  $('section article a').click(function(e){
    // e.preventDefault();
    var url = $(this).attr('href');

    if(url.endsWith('.jpg') || url.endsWith('.gif') || url.endsWith('.png')){
      e.preventDefault();
      img = $(this).find('img')[0]
      console.log(img)
      if(img != undefined){
        console.log("got")
        img.remove();
        return;
      }
      var image = new Image();
      image.src = url;
      $(this).append(image);
    }else{
      return true;
    }
  });

  $(document).on('click', ".loadmore", function(e){
    e.preventDefault();
    if($(e.target).prop('disabled')){
      return
    }
    $(e.target).html('Loading...');
    $(e.target).prop('disabled', true);
    var cid = $(this).data()['cid'];
    $.ajax({
      type: "POST",
      url: '/do/get_comments/' + cid,
      success: function(data) {
        $(e.target).parent().html(data);
      },
      error: function(data, err) {
        $(e.target).prop('disabled', false);
          $(e.target).html('Error while trying to load comments...');
      }
    });
  });

 /******************************************************
                LEGACY AJAX FORMS CODE!
    FOR FUCKS SAKE PORT ALL THIS SHIT TO THE NEW SYSTEM
 *********************************************************/


    function checkErrors(data, div) {
        var obj = data.error,
            ul = $("<ul>");
        for (var i = 0, l = obj.length; i < l; ++i) {
            ul.append("<li>" + obj[i] + "</li>");
        }
        $("#" + div + " .div-error p").html(ul);
        $("#" + div + " .div-error").show();
    }
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

    $("#edit-linkpost-form").submit(function(e) {
        $("#edit-link-btnsubmit").prop('disabled', true);
        $("#edit-link-btnsubmit").text('Editing your post...');
        $.ajax({
            type: "POST",
            url: '/do/edit_linkpost/' + $("#edit-linkpost-form").data('sub') + '/' + $("#edit-linkpost-form").data('pid'), // XXX: Hardcoded URL because this is supposed to be a static file
            data: $("#edit-linkpost-form").serialize(),
            dataType: 'json',
            success: function(data) {
                if (data.status != "ok") {
                    checkErrors(data, "edit-linkpost-form");
                } else {
                    document.location = '/s/' + data.sub + '/' + data.pid;
                }
                $("#edit-linkpost-btnsubmit").prop('disabled', false);
                $("#edit-linkpost-btnsubmit").text('Edit post');
            },
            error: function(data, err) {
                $("#edit-linkpost-form .div-error p").html("<ul><li>Error while contacting the server</li></ul>");
                $("#edit-linkpost-form .div-error").show();
                $("#edit-linkpost-btnsubmit").prop('disabled', false);
                $("#edit-linkpost-btnsubmit").text('Edit post');
            }
        });
        e.preventDefault();
    });


    $("#edit-mod2-form").submit(function(e) {
        $("#edit-mod2-btnsubmit").prop('disabled', true);
        $("#edit-mod2-btnsubmit").text('Inviting mod');
        $.ajax({
            type: "POST",
            url: '/do/inv_mod2/' + $("#edit-mod2-form").data('sub'), // XXX: Hardcoded URL because this is supposed to be a static file
            data: $("#edit-mod2-form").serialize(),
            dataType: 'json',
            success: function(data) {
                if (data.status != "ok") {
                    checkErrors(data, "edit-mod2-form");
                } else {
                    document.location.reload();
                }
                $("#editmod2-btnsubmit").prop('disabled', false);
                $("#editmod2-btnsubmit").text('Invite mod');
            },
            error: function(data, err) {
                $("#edit-mod2-form .div-error p").html("<ul><li>Error while contacting the server</li></ul>");
                $("#edit-mod2-form .div-error").show();
                $("#editmod2-btnsubmit").prop('disabled', false);
                $("#editmod2-btnsubmit").text('Invite mod');
            }
        });
        e.preventDefault();
    });

    $("#ban-user-form").submit(function(e) {
        $("#banuser-btnsubmit").prop('disabled', true);
        $("#banuser-btnsubmit").text('Banning user');
        $.ajax({
            type: "POST",
            url: '/do/ban_user_sub/' + $("#ban-user-form").data('sub'), // XXX: Hardcoded URL because this is supposed to be a static file
            data: $("#ban-user-form").serialize(),
            dataType: 'json',
            success: function(data) {
                if (data.status != "ok") {
                    checkErrors(data, "ban-user-form");
                } else {
                    document.location.reload();
                }
                $("#banuser-btnsubmit").prop('disabled', false);
                $("#banuser-btnsubmit").text('Banhammer');
            },
            error: function(data, err) {
                $("#ban-user-form .div-error p").html("<ul><li>Error while contacting the server</li></ul>");
                $("#ban-user-form .div-error").show();
                $("#banuser-btnsubmit").prop('disabled', false);
                $("#banuser-btnsubmit").text('oops');
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

    $('.delpost').click(function(e){
      $("#delete-post-form input#post").prop('value', $(this).data('post'));
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
    $(document).on('click', '.collapse', function(e){
      var button = $($(e.target).parent());
      if(!button.data('cid')){
        var button = $(e.target);
      }
      var id = button.data('cid');
      $('#comment-'+id).hide();
      $('#child-'+id).hide();
      button.removeClass('collapse');
      button.addClass('expand');
      button.html('<i class="fa fa-plus" aria-hidden="true"></i>')
    });

    $(document).on('click', '.expand', function(e){
      var button = $($(e.target).parent());
      if(!button.data('cid')){
        var button = $(e.target);
      }
      var id = button.data('cid');
      $('#comment-'+id).show();
      $('#child-'+id).show();
      button.removeClass('expand');
      button.addClass('collapse');
      button.html('<i class="fa fa-minus" aria-hidden="true"></i>')
    });
    $(document).on('click', '.lnkreply', function(e) {
      // TODO: Redo this. it's too shitty >_>
      // Explaining what this does because it'll be a pain in the ass to maintain
      // We have stored an additional copy of the form, without the MDE initialized.
      // Here we clone it and remove the 'display: none'
      var x = $($(".comment-form.moving")[0]).clone().show();
      // Here we append it _next_ to the div that is holding the reply button
      $(this).parent().parent().after().after().append(x);
      // Here we hackishly get the textarea and initialize the MDE
      $(x[0]).children('.CommentContent').children('#comment').markdown({autofocus:true})
      //$(e.target).parent().next().insertBefore('<span class="close">×</span>');

      // Here we hide the reply button...
      $(this).parent().hide();
      // Guesswork to get the right elements..
      var parent = $(this).data('to');
      console.log($(this).parent().next())
      // And here we hackishly set the value of the 'parent' hidden input to the cid
      // of the parent comment.
      $('.comment-form.moving #parent').prop('value', parent);
      e.preventDefault();
    });

    $(document).on('click', '.close', function(e) {
        $(this).parent().prev().show();
        $(this).parent().remove();
    });

    var mpSettings = {
        type: 'inline',
        preloader: false,
        callbacks: {
            beforeOpen: function() {
                if ($(window).width() < 700) {
                    this.st.focus = false;
                }
            }
        }
    };
    $('a.popup').magnificPopup(mpSettings);

    $('a.btn.login').magnificPopup(mpSettings);
    $('a.btn.create-sub').magnificPopup(mpSettings);
    $('a.btn.create-post').magnificPopup(mpSettings);
    $('a.btn.send-message').magnificPopup(mpSettings);
    $('a.btn.edit-txtpost-form').magnificPopup(mpSettings);
    $('a.btn.edit-linkpost-form').magnificPopup(mpSettings);
    $('a.btn.delpost').magnificPopup(mpSettings);
    $('a.btn.delete-post-form').magnificPopup(mpSettings);
    $('a.btn.make_announcement-form').magnificPopup(mpSettings);
    $('a.btn.edit-flair-form').magnificPopup(mpSettings);

    $('.edit-comment-form').magnificPopup(mpSettings);
    $('.edit-comment-form').click(function(){
      var cid= $(this).data('cid');
      var sauce=$('#sauce-'+cid).html();
      $('#ecf-cid').prop('value', cid)
      $('#edit-comment-form textarea').html(sauce);
      $('.edit-comment-form').magnificPopup('open');
    });

    $('.delac-close').click(function(e){
      $('.delete-account-form').magnificPopup('close');
      $('#delete_account').prop('value', 0)
      $('#delete_account').prop('checked', false)
    })
    $('#delac').click(function(e){
      $('.delete-account-form').magnificPopup('close');
      $('#delete_account').prop('value', 1)
      $('#delete_account').prop('checked', true)
    })
    $('#delete_account').click(function(e){

      e.preventDefault();
      $('.delete-account-form').magnificPopup('open')
    });
    $('.pmessage .replymsg').click(function(e){
      e.preventDefault();
      var replyto=$(this).parents('article').data('replyto');
      var title=$(this).parents('article').data('replytitle');
      $('#msg-form #to').prop('value', replyto);
      $('#msg-form #subject').prop('value', title);
      var mid = $(e.currentTarget).data().mid
      $.ajax({
        type: "POST",
        url: '/do/read_pm/' + mid,
        dataType: 'json',
        success: function(data) {
          if(data.status == "ok"){
            console.log($(e.currentTarget).parent())
            $(e.currentTarget).parent().children('.unread').text('read')
            $(e.currentTarget).parent().children('.unread').addClass('read').removeClass('unread').removeClass('btn-blue');
          }
        }
      });
    });

    $('.pmessage .replycomment').click(function(e){
      e.preventDefault();

      var sub=$(this).parents('article').data('sub');
      var post=$(this).parents('article').data('post');
      var parent=$(this).parents('article').data('parent');
      $('#comment-form #sub').prop('value', sub);
      $('#comment-form #post').prop('value', post);
      $('#comment-form #parent').prop('value', parent);
    });

    $('.delete-comment-form').magnificPopup(mpSettings);
    $('.delete-comment-form').click(function(){
      var cid= $(this).data('cid');
      $('#dcf-cid').prop('value', cid)
      $('.delete-comment-form').magnificPopup('open');
    });

    $('#xk').magnificPopup(mpSettings);
    $( window ).konami({
        cheat: function() {
            $("body").append('<div id="kx" class="mfp-hide"><iframe src="https://kiwiirc.com/client?settings=5aa9382b84379a9b6a2fe782f4ab85ce" style="border:0; width:100%; height:90vh;"></iframe></div>');
            $("#xk").magnificPopup('open');
        }
    });
    $(document).on('click', '.upvote', function(e){
      var pid = $(e.currentTarget).parent().find('input[name="post"]').prop('value');
      $.ajax({
        type: "POST",
        url: '/do/vote/'+ pid +'/up',
        data: $(e.currentTarget).parent().serialize(),
        dataType: 'json',
        success: function(data) {
          if(data.status == "ok"){
            target = $(e.target)
            if(target[0].classList[0] == 'fa'){
              target = target.parent();
            }

            target.addClass('upvoted');
            target.parent().parent().children('form.dvform').children('.downvote').removeClass('downvoted');
            var count = target.parent().parent().children('.count');
            count.text(parseInt(count.text())+1);
          }
        }
      });
    });
    $(document).on('click', '.downvote', function(e){
      var pid = $(e.currentTarget).parent().find('input[name="post"]').prop('value');
      $.ajax({
        type: "POST",
        url: '/do/vote/'+ pid +'/down',
        data: $(e.currentTarget).parent().serialize(),
        dataType: 'json',
        success: function(data) {
          if(data.status == "ok"){
            target = $(e.target)
            if(target[0].classList[0] == 'fa'){
              target = target.parent();
            }
            target.addClass('downvoted');
            target.parent().parent().children('form.uvform').children('.upvote').removeClass('upvoted');
            var count = target.parent().parent().children('.count');
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

    $('.cdownvote').click(function(e){
      var pid = $(e.currentTarget).parent().find('input[name="post"]').prop('value');
      $.ajax({
        type: "POST",
        url: '/do/votecomment/'+ pid +'/down',
        data: $(e.currentTarget).parent().serialize(),
        dataType: 'json',
        success: function(data) {
          if(data.status == "ok"){
            target = $(e.target)
            if(target[0].classList[0] == 'fa'){
              target = target.parent();
            }
            target.addClass('downvoted');
            $('#cuvform-'+pid).parent().children('.cuvform').children('.upvoted').removeClass('upvoted');

            var count = target.parent().parent().children('.count');
            count.text(parseInt(count.text())-1);
          }
        }
      });
    });

    $('.cupvote').click(function(e){
      var pid = $(e.currentTarget).parent().find('input[name="post"]').prop('value');
      $.ajax({
        type: "POST",
        url: '/do/votecomment/'+ pid +'/up',
        data: $(e.currentTarget).parent().serialize(),
        dataType: 'json',
        success: function(data) {
          if(data.status == "ok"){
            target = $(e.target)
            if(target[0].classList[0] == 'fa'){
              target = target.parent();
            }
            target.addClass('upvoted');
            $('#cuvform-'+pid).parent().children('.cdvform').children('.downvoted').removeClass('downvoted');
            var count = target.parent().parent().children('.count');
            count.text(parseInt(count.text())+1);
          }
        }
      });
    });

    $('.delete').click(function(e){
      var mid = $(e.currentTarget).data().mid
      $.ajax({
        type: "POST",
        url: '/do/delete_pm/' + mid,
        dataType: 'json',
        success: function(data) {
          if(data.status == "ok"){
            $(e.currentTarget).addClass('deleted').removeClass('delete');
            $(e.currentTarget).text('deleted')
          }
        }
      });
    });

    $('.readall').click(function(e){
      var boxid = $(e.currentTarget).data().boxid
      var user = $(e.currentTarget).data().name
      $.ajax({
        type: "POST",
        url: '/do/readall_msgs/' + user + '/' + boxid,
        dataType: 'json',
        success: function(data) {
          if(data.status == "ok"){
            $(e.currentTarget).text('read');
            document.location.reload();
          } else {
            $(e.currentTarget).text('error');
          }
        }
      });
    });

    $('div[id^="assignbadge"]').click(function(e){
      var bid = $(e.currentTarget).data().bid
      var uid = $(e.currentTarget).data().uid
      $.ajax({
        type: "POST",
        url: '/do/assign_user_badge/' + uid + '/' + bid,
        dataType: 'json',
        success: function(data) {
          if(data.status == "ok"){
            $(e.currentTarget).addClass('badgeassigned');
            document.location.reload();
          }
        }
      });
    });

    $('span[id^="removebadge"]').click(function(e){
      var bid = $(e.currentTarget).data().bid
      var uid = $(e.currentTarget).data().uid
      $.ajax({
        type: "POST",
        url: '/do/remove_user_badge/' + uid + '/' + bid,
        dataType: 'json',
        success: function(data) {
          if(data.status == "ok"){
            $(e.currentTarget).text('removed');
            document.location.reload();
          }
        }
      });
    });

    $('span[id^="remove-mod2"]').click(function(e){
      var sub = $(e.currentTarget).data().sub
      var user = $(e.currentTarget).data().user
      $.ajax({
        type: "POST",
        url: '/do/remove_mod2/' + sub + '/' + user,
        dataType: 'json',
        success: function(data) {
          if(data.status == "ok"){
            $(e.currentTarget).removeClass('active').addClass('removed');
            $(e.currentTarget).text('removed');
          } else {
            $(e.currentTarget).text('error');
          }
        }
      });
    });

    $('span[id^="revoke-ban"]').click(function(e){
      var sub = $(e.currentTarget).data().sub
      var user = $(e.currentTarget).data().user
      $.ajax({
        type: "POST",
        url: '/do/remove_sub_ban/' + sub + '/' + user,
        dataType: 'json',
        success: function(data) {
          if(data.status == "ok"){
            $(e.currentTarget).removeClass('revoke').addClass('accepted');
            $(e.currentTarget).text('un-banned');
          } else {
            $(e.currentTarget).text('error');
          }
        }
      });
    });

    $('span[id^="revoke-mod2-inv"]').click(function(e){
      var sub = $(e.currentTarget).data().sub
      var user = $(e.currentTarget).data().user
      $.ajax({
        type: "POST",
        url: '/do/revoke_mod2inv/' + sub + '/' + user,
        dataType: 'json',
        success: function(data) {
          if(data.status == "ok"){
            $(e.currentTarget).removeClass('revoke').addClass('revoked');
            $(e.currentTarget).text('revoked');
          } else {
            $(e.currentTarget).text('error');
          }
        }
      });
    });

    $('span[id^="accept-mod2-inv"]').click(function(e){
      var sub = $(e.currentTarget).data().sub
      var user = $(e.currentTarget).data().user
      $.ajax({
        type: "POST",
        url: '/do/accept_mod2inv/' + sub + '/' + user,
        dataType: 'json',
        success: function(data) {
          if(data.status == "ok"){
            $(e.currentTarget).addClass('accepted');
            $(e.currentTarget).text('Welcome aboard');
          } else {
            $(e.currentTarget).text('error');
          }
        }
      });
    });

    $('span[id^="refuse-mod2-inv"]').click(function(e){
      var sub = $(e.currentTarget).data().sub
      var user = $(e.currentTarget).data().user
      $.ajax({
        type: "POST",
        url: '/do/refuse_mod2inv/' + sub + '/' + user,
        dataType: 'json',
        success: function(data) {
          if(data.status == "ok"){
            $(e.currentTarget).addClass('refused');
            $(e.currentTarget).text('kthnxby');
          } else {
            $(e.currentTarget).text('error');
          }
        }
      });
    });

    $('span[id^="deletesubflair"]').click(function(e){
      var sub = $(e.currentTarget).data().sub
      var fl = $(e.currentTarget).data().fl
      $.ajax({
        type: "POST",
        url: '/do/delete_sub_flair/' + sub + '/' + fl,
        dataType: 'json',
        success: function(data) {
          if(data.status == "ok"){
            $(e.currentTarget).text('deleted');
            document.location.reload();
          } else {
            $(e.currentTarget).text('error');
          }
        }
      });
    });

    $('label.assignpostflair').click(function(e){
      var sub = $(e.currentTarget).data().sub
      var post = $(e.currentTarget).data().post
      var fl = $(e.currentTarget).data().fl
      $.ajax({
        type: "POST",
        url: '/do/assign_post_flair/' + sub + '/' + post + '/' + fl,
        dataType: 'json',
        success: function(data) {
          if(data.status == "ok"){
            $(e.currentTarget).text('assigned');
            document.location.reload();
          } else {
            $(e.currentTarget).text('error');
          }
        }
      });
    });

    $('div[id^="removepostflair"]').click(function(e){
      var sub = $(e.currentTarget).data().sub
      var post = $(e.currentTarget).data().post
      $.ajax({
        type: "POST",
        url: '/do/remove_post_flair/' + sub + '/' + post,
        dataType: 'json',
        success: function(data) {
          if(data.status == "ok"){
            $(e.currentTarget).text('removed');
            document.location.reload();
          } else {
            $(e.currentTarget).text('error');
          }
        }
      });
    });
    $('span[id^="subscribe"').click(function(e){
      var sid = $(e.currentTarget).data().sid
      if($(this).hasClass('unsubscribed'))  {
        $.ajax({
          type: "POST",
          url: '/do/subscribe/' + sid,
          dataType: 'json',
          success: function(data) {
            if(data.status == "ok"){
              $(e.currentTarget).removeClass('unsubscribed').addClass('subscribed');
              $(e.currentTarget).html('<a class="btn small"><i class="fa fa-check" aria-hidden="true"></i> Subscribed</a>');
              if($('.sidebar span[id^="block"]').hasClass('blocked')) {
                $('.sidebar span[id^="block"]').removeClass('blocked').addClass('unblocked');
                $('.sidebar span[id^="block"]').html('<a class="btn small"><i class="fa fa-remove" aria-hidden="true"></i> Block</a>');
              }
            }
          }
        });
      } else {
        $.ajax({
          type: "POST",
          url: '/do/unsubscribe/' + sid,
          dataType: 'json',
          success: function(data) {
            if(data.status == "ok"){
              $(e.currentTarget).removeClass('subscribed').addClass('unsubscribed');
              $(e.currentTarget).html('<a class="btn small"><i class="fa fa-plus" aria-hidden="true"></i> Subscribe</a>');
            }
          }
        });
      }
    });
    $('span[id^="block"').click(function(e){
      var sid = $(e.currentTarget).data().sid
      if($(this).hasClass('unblocked'))  {
        $.ajax({
          type: "POST",
          url: '/do/block/' + sid,
          dataType: 'json',
          success: function(data) {
            if(data.status == "ok"){
              $(e.currentTarget).removeClass('unblocked').addClass('blocked');
              $(e.currentTarget).html('<a class="btn small"><i class="fa fa-check" aria-hidden="true"></i> Blocked</a>');
              if($('.sidebar span[id^="subscribe"]').hasClass('subscribed')) {
                $('.sidebar span[id^="subscribe"]').removeClass('subscribed').addClass('unsubscribed');
                $('.sidebar span[id^="subscribe"]').html('<a class="btn small"><i class="fa fa-plus" aria-hidden="true"></i> Subscribe</a>');
              }
            }
          }
        });
      } else {
        $.ajax({
          type: "POST",
          url: '/do/unblock/' + sid,
          dataType: 'json',
          success: function(data) {
            if(data.status == "ok"){
              $(e.currentTarget).removeClass('blocked').addClass('unblocked');
              $(e.currentTarget).html('<a class="btn small"><i class="fa fa-remove" aria-hidden="true"></i> Block</a>');
            }
          }
        });
      }
    });
    $(document).on('click', 'span[id^="youtubevid"]', function(e){
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
    $(document).on('click', 'span[id^="vimeovid"]', function(e){
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
    $(document).on('click', 'span[id^="vinevid"]', function(e){
      var pid = $(e.currentTarget).data().pid
      var url = $(e.currentTarget).data().vid
      var frame = document.createElement('iframe');
      if($(this).hasClass('closedvine'))  {
        frame.width = '520px';
        frame.height = '520px';
        frame.style = 'display:block;';
        frame.frameborder = '0';
        frame.src = 'https://vine.co/v/' + vineID(url) + '/embed/simple';
        playerid = 'player' + pid;
        $(e.currentTarget).addClass('openedvine').removeClass('closedvine');
        document.getElementById(playerid).appendChild(frame);
        $('#' + playerid + ' a').html('<i class="fa fa-close" aria-hidden="true"></i>');
      }
      else {
        $(this).addClass('closedvine').removeClass('openedvine');
        $('#' + playerid + ' iframe').remove();
        $('#' + playerid + ' a').html('<i class="fa fa-vine" aria-hidden="true"></i>');

      }
    });
    $(document).on('click', 'span[id^="gfycat"]', function(e){
      var pid = $(e.currentTarget).data().pid
      var url = $(e.currentTarget).data().vid
      var frame = document.createElement('iframe');
      if($(this).hasClass('closedgfycat'))  {
        frame.width = '520px';
        frame.height = '460px';
        frame.style = 'display:block;';
        frame.frameborder = '0';
        frame.src = 'https://gfycat.com/ifr/' + gfycatID(url);
        playerid = 'player' + pid;
        $(e.currentTarget).addClass('openedgfycat').removeClass('closedgfycat');
        document.getElementById(playerid).appendChild(frame);
        $('#' + playerid + ' a').html('<i class="fa fa-close" aria-hidden="true"></i>');
      }
      else {
        $(this).addClass('closedgfycat').removeClass('openedgfycat');
        $('#' + playerid + ' iframe').remove();
        $('#' + playerid + ' a').html('<i class="fa fa-video-camera" aria-hidden="true"></i>');

      }
    });
    $(document).on('click', 'span[id^="openimg"]', function(e){
      var pid = $(e.currentTarget).data().pid
      var url = $(e.currentTarget).data().img
      var img = document.createElement('img');
      playerid = 'player' + pid;
      if($(this).hasClass('closedimg'))  {
        img.style = 'max-width:100%;display:block;';
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
    $(document).on('click', 'span[id^="openvid"]', function(e){
      var pid = $(e.currentTarget).data().pid
      var domain = $(e.currentTarget).data().domain
      var url = $(e.currentTarget).data().vid
      var player = document.createElement('video');
      var source = document.createElement('source');
      playerid = 'player' + pid;
      if($(this).hasClass('closedvid'))  {
        player.id = "vid" + pid
        player.style = 'max-width:560px;display:block;';
        player.preload ="auto"
        player.autoplay = "autoplay"
        player.loop = "loop"
        source.type = "video/webm"
        if (domain == "i.imgtc.com") {
          source.src = 'https://i.imgtc.com/' + imgtcID(url);
        } else {
          source.src = url
        }
        $(e.currentTarget).addClass('openedvid').removeClass('closedvid');
        document.getElementById(playerid).appendChild(player);
        document.getElementById("vid" + pid).appendChild(source);
        $('#' + playerid + ' a').html('<i class="fa fa-close" aria-hidden="true"></i>');
      }
      else {
        $(this).addClass('closedvid').removeClass('openedvid');
        $('#' + playerid + ' video').remove()
        $('#' + playerid + ' a').html('<i class="fa fa-play" aria-hidden="true"></i>');
      }
    });
    $(document).on('click', 'span[id^="gifv"]', function(e){
      var pid = $(e.currentTarget).data().pid
      var domain = $(e.currentTarget).data().domain
      var url = $(e.currentTarget).data().vid
      var player = document.createElement('video');
      var source = document.createElement('source');
      playerid = 'player' + pid;
      if($(this).hasClass('closedgifv'))  {
        player.id = "vid" + pid
        player.style = 'max-width:560px;display:block;';
        player.preload ="auto"
        player.autoplay = "autoplay"
        player.loop = "loop"
        if (domain == "i.imgur.com" || domain == "imgur.com") {
          source.src = 'https://i.imgur.com/' + imgurID(url) + '.mp4';
        }
        if (domain == "i.sli.mg") {
          source.src = 'https://i.sli.mg/' + slimgID(url) + '.webm';
        }
        source.type = "video/webm"
        $(e.currentTarget).addClass('openedgifv').removeClass('closedgifv');
        document.getElementById(playerid).appendChild(player);
        document.getElementById("vid" + pid).appendChild(source);
        $('#' + playerid + ' a').html('<i class="fa fa-close" aria-hidden="true"></i>');
      }
      else {
        $(this).addClass('closedgifv').removeClass('openedgifv');
        $('#' + playerid + ' video').remove();
        $('#' + playerid + ' a').html('<i class="fa fa-video-camera" aria-hidden="true"></i>');

      }
    });
    $(document).on('click', 'span[id^="tweet"]', function(e){
      var pid = $(e.currentTarget).data().pid
      var url = $(e.currentTarget).data().url
      var div = document.createElement('div');
      playerid = 'player' + pid;
      if($(this).hasClass('closedtweet'))  {
        $.ajax({
          type: "get",
          url: 'https://publish.twitter.com/oembed?url=' + url,
          dataType: 'jsonp',
          success: function(data) {
            if(data.version == "1.0"){
              div.innerHTML = data.html;
            } else {
              div.innerHTML = '<br>Oops. Phox got my tounge. Something borked.<br>';
            }
          }
        });

        $(e.currentTarget).addClass('openedtweet').removeClass('closedtweet');
        document.getElementById(playerid).appendChild(div);
        $('#' + playerid + ' a').html('<i class="fa fa-close" aria-hidden="true"></i>');
      }
      else {
        $(this).addClass('closedtweet').removeClass('openedtweet');
        $('#' + playerid + ' div').remove()
        $('#' + playerid + ' a').html('<i class="fa fa-twitter" aria-hidden="true"></i>');
      }
    });
    $(document).on('click', 'span[id^="opentextpost"]', function(e){
      var pid = $(e.currentTarget).data().pid
      var div = document.createElement('div');
      playerid = 'player' + pid;
      if($(this).hasClass('closedtextpost'))  {
        div.id = 'content';
        $.ajax({
            type: "GET",
            url: '/do/get_txtpost/' + pid, // XXX: Hardcoded URL
            dataType: 'json',
            success: function(data) {
                if (data.status == "ok") {
                    div.innerHTML = data.content;
                }

            }
        });
        $(e.currentTarget).addClass('openedtextpost').removeClass('closedtextpost');
        document.getElementById(playerid).appendChild(div);
        $('#' + playerid + ' a').html('<i class="fa fa-close" aria-hidden="true"></i>');
      }
      else {
        if($(e.currentTarget)[0].id=="opentextpost" && e.target==$('#' + playerid + ' div')[0]){
          return;
        }
        $(this).addClass('closedtextpost').removeClass('openedtextpost');
        $('#' + playerid + ' div').remove()
        $('#' + playerid + ' a').html('<i class="fa fa-comments" aria-hidden="true"></i>');
      }
    });

    $("#create-user-badge").submit(function(e) {
        $("#create-user-badge-btnsubmit").prop('disabled', true);
        $("#create-user-badge-btnsubmit").text('Creating badge...');
        $.ajax({
            type: "POST",
            url: '/do/create_user_badge', // XXX: Hardcoded URL because this is supposed to be a static file
            data: $("#create-user-badge").serialize(),
            dataType: 'json',
            success: function(data) {
                if (data.status != "ok") {
                    checkErrors(data, "create-user-badge");
                } else { // success
                    document.location.reload();
                }
                $("#create-user-badge-btnsubmit").prop('disabled', false);
                $("#create-user-badge-btnsubmit").text('Create badge');
            },
            error: function(data, err) {
                $("#create-user-badge .div-error p").append("<ul><li>Error while contacting the server</li></ul>");
                $("#create-user-badge .div-error").show();
                $("#create-user-badge-btnsubmit").prop('disabled', false);
                $("#create-user-badge-btnsubmit").text('Create badge');
            }
        });

        e.preventDefault();
    });

    $("#usebtcdonation").submit(function(e) {
        $("#usebtcdonation-btnsubmit").prop('disabled', true);
        $("#usebtcdonation-btnsubmit").text('saving...');
        $.ajax({
            type: "POST",
            url: '/do/usebtcdonation', // XXX: Hardcoded URL because this is supposed to be a static file
            data: $("#usebtcdonation").serialize(),
            dataType: 'json',
            success: function(data) {
                if (data.status != "ok") {
                    checkErrors(data, "usebtcdonation");
                } else { // success
                    document.location.reload();
                }
                $("#usebtcdonation-btnsubmit").prop('disabled', false);
                $("#usebtcdonation-btnsubmit").text('Saved!');
            },
            error: function(data, err) {
                $("#usebtcdonation .div-error p").append("<ul><li>Error while contacting the server</li></ul>");
                $("#usebtcdonation .div-error").show();
                $("#usebtcdonation-btnsubmit").prop('disabled', false);
                $("#usebtcdonation-btnsubmit").text('Save');
            }
        });

        e.preventDefault();
    });

    $('#subsdropdown').click(function(){
      var w = $('#subslist').width()
      var x = ''
       $.each($("#subslist .subinthebar"),function(){
           p = $(this).position();
           if (p.left < 0 - $(this).width() || p.left > w){
              console.log($(this))
              x = x + '<li>' + $(this).html() + '</li>'
           }
       });
       $('#hiddensubs').html(x)
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
function vineID(url) {
  var match = url.match(/^http(?:s?):\/\/(?:www\.)?vine\.co\/v\/([a-zA-Z0-9]{1,13})$/);
  if (match){
    return match[1];
	}
}
function gfycatID(url) {
  var match = url.match(/^http(?:s?):\/\/gfycat\.com\/([a-zA-Z0-9]{1,60})$/);
  if (match){
    return match[1];
	}
}
function imgurID(url) {
  var match = url.match(/^http(?:s?):\/\/(i\.)?imgur\.com\/(.*?)(?:\/.gifv|$)/);
  if (match){
    return match[2].replace(/.gifv/,'');
	}
}
function slimgID(url) {
  var match = url.match(/^http(?:s?):\/\/(i\.)?sli\.mg\/(.*?)(?:\/.gifv|$)/);
  if (match){
    return match[2].replace(/.gifv/,'');
	}
}
function imgtcID(url) {
  var match = url.match(/^http(?:s?):\/\/(i\.)?imgtc\.com\/(.*?)(?:\/.mp4|$)/);
  if (match){
    return match[2];
	}
}
