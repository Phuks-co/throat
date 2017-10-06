// Message pages
// import TextConfirm from  './utils/TextConfirm';
// import Icons from './Icon';
import $ from 'jquery';

// Mark message as read.
$('.readmsg').click(function(e){
  var mid = $(e.currentTarget).data().mid;
  $.ajax({
    type: "POST",
    url: '/do/read_pm/' + mid,
    dataType: 'json',
    success: function(data) {
      $(e.currentTarget).text('read');
      $(e.currentTarget).removeClass("readmsg").addClass("read");
      $(e.currentTarget).parent().parent().parent().removeClass("newmsg");
    }
  });
});

// Saving/unsaving message.
$('.savemsg').click(function(e){
  var mid = $(e.currentTarget).data().mid;
  $.ajax({
    type: "POST",
    url: '/do/save_pm/' + mid,
    dataType: 'json',
    success: function(data) {
      $(e.currentTarget).text('saved');
      $(e.currentTarget).removeClass("savemsg").addClass("savedmsg");

    }
  });
});

// Delete message.
$('.deletemsg').click(function(e){
  var mid = $(e.currentTarget).data().mid;
  $.ajax({
    type: "POST",
    url: '/do/delete_pm/' + mid,
    dataType: 'json',
    success: function(data) {
      $(e.currentTarget).text('deleted');
      $(e.currentTarget).removeClass("deletemsg").addClass("deletedmsg");
    }
  });
});
