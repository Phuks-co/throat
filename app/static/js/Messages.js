// Message pages
// import TextConfirm from  './utils/TextConfirm';
// import Icons from './Icon';
import u from './Util';

// Mark message as read.
u.sub('.readmsg', 'click', function(e){
  var mid = this.getAttribute('data-mid'),obj=this;
  u.post('/do/read_pm/'+mid, {},
  function(data){
    if (data.status == "ok") {
      obj.innerHTML = 'read';
      obj.classList.remove('readmsg');
      obj.classList.add('read');
      obj.parentNode.parentNode.parentNode.classList.remove('newmsg');
    }
  });
});

// Saving/unsaving message.
u.sub('.savemsg', 'click', function(e){
  var mid = this.getAttribute('data-mid'),obj=this;
  u.post('/do/save_pm/'+mid, {},
  function(data){
    if (data.status == "ok") {
      obj.innerHTML = 'saved';
      obj.classList.remove('savemsg');
      obj.classList.add('savedmsg');
    }
  });
});

// Delete message.
u.sub('.deletemsg', 'click', function(e){
  var mid = this.getAttribute('data-mid'),obj=this;
  u.post('/do/delete_pm/'+mid, {},
  function(data){
    if (data.status == "ok") {
      obj.innerHTML = 'deleted';
      obj.classList.remove('deletemsg');
      obj.classList.add('deletedmsg');
    }
  });
});

// Toggle message reply
u.sub('.pmessage .replymsg', 'click', function(e){
  e.preventDefault();
  var replyto = this.getAttribute('data-replyto')
  var title = this.getAttribute('data-replytitle')
  var mid = this.getAttribute('data-mid')
  document.querySelector('#msg-form #to').setAttribute('value', replyto);
  if(document.querySelector('#msg-form #lto')){
    document.querySelector('#msg-form #lto').style.display = 'none';
  }
  document.querySelector('#msg-form #subject').setAttribute('value', 'Re:' + title);
  var modal = document.getElementById('msgpop');
  document.querySelector('#replyto'+mid).appendChild(document.getElementById('msgpop'));
  modal.style.display = "block";
});

u.sub('.pmessage .formpopmsg', 'click', function(e){
  e.preventDefault();
  var replyto = this.getAttribute('data-replyto')
  document.querySelector('#msg-form #to').setAttribute('value', replyto);
  var modal = document.getElementById('formpop');
  modal.style.display = "block";
});

u.sub('.pmessage .replycom', 'click', function(e){
  var replyto = this.getAttribute('data-replyto')
  var post = this.getAttribute('data-post')
  var sub = this.getAttribute('data-sub')
  var parentid = this.getAttribute('data-parentid')
  var mid = this.getAttribute('data-mid')
  document.querySelector('#comment-form #from').innerHTML = replyto;
  document.querySelector('#comment-form #sub').innerHTML = sub;
  document.querySelector('#comment-form #post').setAttribute('value', post);
  document.querySelector('#comment-form #sub').setAttribute('value', sub);
  document.querySelector('#comment-form #parent').setAttribute('value', parentid);
  var modal = document.getElementById('msgpop');
  document.querySelector('#replyto'+mid).appendChild(document.getElementById('msgpop'));
  modal.style.display = "block";
});

u.addEventForChild(document, 'click', '.closemsg', function(e, qelem){
  e.preventDefault();
  qelem.parentNode.style.display = 'none';
});
u.addEventForChild(document, 'click', '.closepopmsg', function(e, qelem){
  e.preventDefault();
  this.parentNode.parentNode.style.display = 'none';
});
