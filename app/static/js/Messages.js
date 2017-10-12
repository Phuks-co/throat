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

// Toggle message reply
$('.pmessage .replymsg').click(function(e){
  e.preventDefault();
  var replyto = $(e.currentTarget).data().replyto
  var title = $(e.currentTarget).data().replytitle
  var mid = $(e.currentTarget).data().mid
  $('#msg-form #to').prop('value', replyto);
  $('#msg-form #lto').hide();
  $('#msg-form #subject').prop('value', 'Re:' + title);
  var modal = document.getElementById('msgpop');
  $("#msgpop").appendTo("#replyto" + mid);
  modal.style.display = "block";
});
$('.pmessage .formpopmsg').click(function(e){
  e.preventDefault();
  var replyto = $(e.currentTarget).data().replyto
  $('#msg-form #to').prop('value', replyto);
  $('#msg-form #lto').hide();
  var modal = document.getElementById('formpop');
  modal.style.display = "block";
});
$('.createsub').click(function(e){
  e.preventDefault();
  var modal = document.getElementById('formpop');
  modal.style.display = "block";
});
$('.pmessage .replycom').click(function(e){
  e.preventDefault();
  var replyto = $(e.currentTarget).data().replyto
  var post = $(e.currentTarget).data().post
  var sub = $(e.currentTarget).data().sub
  var parentid = $(e.currentTarget).data().parentid
  var mid = $(e.currentTarget).data().mid
  $('#comment-form #from').text(replyto);
  $('#comment-form #sub').text(sub);
  $('#comment-form #post').prop('value', post);
  $('#comment-form #sub').prop('value', sub);
  $('#comment-form #parent').prop('value', parentid);
  var modal = document.getElementById('msgpop');
  $("#msgpop").appendTo("#replyto" + mid);
  modal.style.display = "block";
});

$('#msgpop .closemsg').click(function(e){
  e.preventDefault();
  var modal = document.getElementById('msgpop');
  modal.style.display = "none";
});
$('#formpop .closemsg').click(function(e){
  e.preventDefault();
  var modal = document.getElementById('formpop');
  modal.style.display = "none";
});
