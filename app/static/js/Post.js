// Post page-related code.
import TextConfirm from  './utils/TextConfirm';
import $ from 'jquery';
import Icons from './Icon';

// Saving/unsaving posts.
$('.savepost').click(function(e){
  var pid = $(e.currentTarget).data().pid;
  $.ajax({
    type: "POST",
    url: '/do/save_post/' + pid,
    dataType: 'json',
    success: function(data) {
      $(e.currentTarget).text('saved');
    }
  });
});

$('.removesavedpost').click(function(e){
  var pid = $(e.currentTarget).data().pid;
  $.ajax({
    type: "POST",
    url: '/do/remove_saved_post/' + pid,
    dataType: 'json',
    success: function(data) {
      if(data.status == "ok"){
        $(e.currentTarget).text('removed');
      } else {
        $(e.currentTarget).text('oops');
      }
    }
  });
});

// Delete post
$(document).on('click', '.delete-post', function(){
  // confirmation
  TextConfirm(this, function(){
    $.ajax({
      type: "POST",
      url: '/do/delete_post',
      data: $("#delete-post-form").serialize(),
      dataType: 'json',
      success: function(data) {
          if (data.status != "ok") {
            $(this).parent().html('There was an error while deleting your post.');
          } else {
            $(this).parent().html('Post removed');
            document.location.reload();
          }
      },
      error: function(data, err) {
          $(this).parent().html('could not contact server');
      }
    });
  });
});

// Stick post
$(document).on('click', '.stick-post', function(){
  // confirmation
  var pid = $(this).parent().parent().data('pid');
  TextConfirm(this, function(){
    $.ajax({
      type: "POST",
      url: '/do/stick/' + pid,
      data: $("#delete-post-form").serialize(),
      dataType: 'json',
      success: function(data) {
          if (data.status != "ok") {
            $(this).parent().html('Error.');
          } else {
            $(this).parent().html('Done!');
            document.location.reload();
          }
      },
      error: function(data, err) {
          $(this).parent().html('could not contact server');
      }
    });
  });
});

// post source
$(document).on('click', '.post-source', function(){
  var elem = document.getElementById('postcontent');
  var oc = elem.innerHTML;
  var back =  document.createElement( "a" );
  back.innerHTML = "<s>source</s>";
  back.onclick = function(){
    elem.innerHTML = oc;
    $(this).parent().html('<a class="post-source">source</a>');
  };
  var h = elem.clientHeight-6;
  elem.innerHTML = '<textarea style="height: ' + h + 'px">' + document.getElementById('post-source').innerHTML + '</textarea>';
  $(this).parent().html(back);
});


// comment source
$(document).on('click', '.comment-source', function(){
  var cid = $(this).data('cid');
  var elem = document.getElementById('content-' + cid);
  var oc = elem.innerHTML;
  var back =  document.createElement( "a" );
  back.innerHTML = "<s>source</s>";
  back.onclick = function(){
    elem.innerHTML = oc;
    $(this).parent().html('source');
  };
  var h = elem.clientHeight + 28;
  elem.innerHTML = '<textarea style="height: ' + h + 'px">' + document.getElementById('sauce-' + cid).innerHTML + '</textarea>';
  $(this).html(back);
});


// Delete comment
$(document).on('click', '.delete-comment', function(){
  // confirmation
  var cid = $(this).data('cid');
  $("#dcf-cid").val(cid);
  TextConfirm(this, function(){
    $.ajax({
      type: "POST",
      url: '/do/delete_comment',
      data: $("#delete-comment-form").serialize(),
      dataType: 'json',
      success: function(data) {
          if (data.status != "ok") {
            $(this).parent().html('There was an error while deleting the comment.');
          } else {
            $(this).parent().html('Comment removed');
            document.location.reload();
          }
      },
      error: function(data, err) {
          $(this).parent().html('could not contact server');
      }
    });
  });
});

// Grab post title from url
$(document).on('click', '#graburl', function(){
  $(this).prop('disabled', true);
  $(this).html('Grabbing...');
  $.ajax({
    type: "GET",
    dataType: 'json',
    url: '/do/grabtitle',
    data: {'u': $('#link').prop('value')},
    success: function(data) {
      if(data.status == 'error'){
        $('#title').prop('value', 'Error fetching title');
        $('#graburl').prop('disabled', false);
        $('#graburl').html('Grab title');
      }else{
        $('#title').prop('value', data.title);
        $('#graburl').prop('disabled', false);
        $('#graburl').html('Done!');
      }
    }
  });
});

// Load children
$(document).on('click', '.loadchildren', function(e){
  e.preventDefault();
  var ob = $(this)
  $.ajax({
    type: "POST",
    dataType: 'json',
    url: '/do/get_children/' + $(this).data('pid') + '/' + $(this).data('cid'),
    dataType: 'html',
    success: function(data){
      ob.parent().html(data);
      $('div[data-icon],span[data-icon]').each(function(i){
        this.innerHTML = Icons[$(this).data('icon')];
      });
    }
  });
});

$(document).on('click', '.loadsibling', function(e){
  e.preventDefault();
  var ob = $(this)
  var page = (ob.data('page') !== '') ? ob.data('page') : 1;
  var parent = (ob.data('cid') !== '') ? ob.data('cid') : 1;
  $.ajax({
    type: "POST",
    dataType: 'json',
    url: '/do/get_sibling/' + $(this).data('pid') + '/' + parent + '/' + page,
    dataType: 'html',
    success: function(data){
      ob.replaceWith(data);
      $('div[data-icon],span[data-icon]').each(function(i){
        this.innerHTML = Icons[$(this).data('icon')];
      });
    }
  });
});

// collapse/expand comment
$(document).on('click', '.togglecomment.collapse', function(e){
  e.preventDefault();
  var cid = $(this).data('cid');
  $('#comment-'+cid+' .votecomment').hide();
  $('#comment-'+cid+' .bottombar').hide();
  $('#comment-'+cid+' .commblock .content').hide();
  $('#'+cid+' .pchild').hide();
  $(this).removeClass('collapse');
  $(this).addClass('expand');
  $(this).parent().parent().css('margin-left', '1.3em');
  $(this).text = '[+]';
})

$(document).on('click', '.togglecomment.expand', function(e){
  e.preventDefault();
  var cid = $(this).data('cid');
  $('#comment-'+cid+' .votecomment').show();
  $('#comment-'+cid+' .bottombar').show();
  $('#child-'+cid).show();
  $('#content-'+cid).show();
  $(this).removeClass('expand');
  $(this).addClass('collapse');
  $(this).text = '[-]';
  $(this).parent().parent().css('margin-left', '0');
})
