// Post page-related code.
import TextConfirm from  './utils/TextConfirm';
import $ from 'jquery';

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
