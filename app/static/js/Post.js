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
