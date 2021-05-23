// Message pages
// import TextConfirm from  './utils/TextConfirm';
// import Icons from './Icon';
import u from './Util';
import _ from './utils/I18n';

// Mark message as read.
u.sub('.readmsg', 'click', function(e){
  var mid = this.getAttribute('data-mid'),obj=this;
  u.post('/do/read_pm/'+mid, {},
  function(data){
    if (data.status == "ok") {
      obj.parentNode.parentNode.parentNode.classList.remove('newmsg');
      obj.remove();
    }
  });
});

u.sub('.markall', 'click', function(e){
  u.post('/do/readall_msgs', {},
  function(data){
    if (data.status == "ok") {
      document.location.reload();
    }
  });
});

// Saving/unsaving message.
u.sub('.savemsg', 'click', function(e){
  var mid = this.getAttribute('data-mid'),obj=this;
  u.post('/do/save_pm/'+mid, {},
  function(data){
    if (data.status == "ok") {
      obj.innerHTML = _('saved');
      obj.classList.remove('savemsg');
      obj.classList.add('savedmsg');
    }
  });
});

// Delete notification.
u.sub('.deletemsg', 'click', function(e){
  const mid = this.getAttribute('data-mid'), obj = this;
  u.post('/do/delete_pm/'+mid, {},
  function(data){
    if (data.status == "ok") {
      obj.innerHTML = _('deleted');
      obj.classList.remove('deletemsg');
      obj.classList.add('deletedmsg');
    }
  });
});

u.sub('.deletenotif', 'click', function(e){
  const mid = this.getAttribute('data-mid'), obj = this;
  u.post('/messages/notifications/delete/'+mid, {},
  function(data){
    if (data.status == "ok") {
      obj.innerHTML = _('deleted');
      obj.classList.remove('deletemsg');
      obj.classList.add('deletedmsg');
    }
  });
});

// Show message reply
u.sub('.pmessage .replymsg', 'click', function(e){
  e.preventDefault();
  var mid = this.getAttribute('data-mid')
  document.querySelector('#msg-form #mid').setAttribute('value', mid);
  var modal = document.getElementById('msgpop');
  var existingParent = modal.parentNode;
  var newParent = document.querySelector('#replyto'+mid);
  if (existingParent != newParent) {
    var markdownEditor = document.querySelector('#msg-form #content')
    var existingContent = markdownEditor.value;
    var newContent = newParent.getAttribute('data-content');
    existingParent.setAttribute('data-content', existingContent);
    newParent.appendChild(modal);
    markdownEditor.value = newContent ? newContent : '';
    document.querySelector('.cmpreview').style.display = 'none';
  }
  modal.style.display = "block";
});

u.sub('.pmessage .formpopmsg', 'click', function(e){
  e.preventDefault();
  var replyto = this.getAttribute('data-replyto')
  document.querySelector('#msg-form #to').setAttribute('value', replyto);
  var modal = document.getElementById('formpop');
  modal.style.display = "block";
});

u.addEventForChild(document, 'click', '.closemsg', function(e, qelem){
  e.preventDefault();
  qelem.parentNode.style.display = 'none';
});
u.addEventForChild(document, 'click', '.closepopmsg', function(e, qelem){
  e.preventDefault();
  qelem.parentNode.parentNode.style.display = 'none';
});

u.sub('.block', 'click', function(e){
  const uid = this.getAttribute('data-uid'),obj=this;
  u.post('/do/toggle_ignore/'+uid, {},
  function(data){
    if (data.status == "ok") {
      if(obj.innerHTML.trim() == _('block')){
        u.each('a[data-uid="' + uid + '"]', function(el,i){el.innerHTML = _('unblock');});
      }else{
        u.each('a[data-uid="' + uid + '"]', function(el,i){el.innerHTML = _('block');});
      }
    }
  });

});
