import io from 'socket.io-client';
import icon from './Icon'
import u from './Util';
import anchorme from "anchorme";
import _ from './utils/I18n';
import Tinycon from 'tinycon'
RegExp.escape= function(s) {
    return s.replace(/[-\/\\^$*+?.()|[\]{}]/g, '\\$&');
};

Tinycon.setOptions({
    height: 11,
	font: '10px arial',
	color: '#ffffff',
	background: '#000000',
	fallback: true
});


const socket = io('///snt', {transports: ['websocket'], upgrade: false});

function updateNotifications(count){
  if(count == 0){
    document.getElementById('mailcount').innerHTML = '';
    document.getElementById('mailcount').style.display = 'none';
  }else{
    document.getElementById('mailcount').innerHTML = count;
    document.getElementById('mailcount').style.display = 'inline-block';
  }
}

function updateModNotifications(notifications) {
  const modElem = document.getElementById('modcount');
  if (modElem) {
    let sum = 0;
    for (let i=0; i < notifications.length; i++) {
      sum = sum + notifications[i][1];
    }
    if (sum == 0) {
      modElem.innerHTML = '';
      modElem.style.display = 'none';
    } else {
      modElem.innerHTML = sum.toString();
      modElem.style.display = 'inline-block';
    }
  }
}

function updateTitleNotifications() {
  let count = 0;
  const mailcount = document.getElementById('mailcount');
  if (mailcount) {
    count += Number(mailcount.innerHTML);
  }
  const modcount = document.getElementById('modcount');
  if (modcount) {
    count += Number(modcount.innerHTML);
  }

  Tinycon.setBubble(count)
}


var modData = [];

// Get the mod notifications if present, and update the title bar with
// the total number of notifications (for both mods and non-mods).
u.ready(function () {
  var modElem = document.getElementById('modcount');
  if (modElem) {
    modData = JSON.parse(modElem.getAttribute('data-mod'));
      updateModNotifications(modData);
  }
  updateTitleNotifications();
})


// Thumbnails, lazy and deferred loading.  If a thumbnail exists,
// wait until the page is loaded to put it into the src attribute
// of the image element so the browser can start rendering
// the page.  If a thumbnail is still being calculated, listen
// for the socketio message announcing its completion and insert
// it where it belongs.

function loadLazy() {
  var lazy = document.getElementsByClassName('lazy');
  for (var i = 0; i < lazy.length; i++) {
    var data_src = lazy[i].getAttribute('data-src');
    if (data_src) {
      lazy[i].src = data_src;
      lazy[i].removeAttribute('data-src');
    }
    lazy[i].classList.remove('lazy;')
  }
}

socket.loadLazy = loadLazy;


function subscribeDeferred() {
  var deferred = document.getElementsByClassName('deferred');

  // Set up the callback for a thumbnail event.
  socket.on('thumbnail', function(data) {
    for (var i = 0; i < deferred.length; i++) {
      if (deferred[i].getAttribute('data-deferred') == data.target &&
          data.thumbnail != '') {
        var elem = deferred[i];
        if (elem.tagName == 'IMG') {
          elem.src = data.thumbnail;
          elem.classList.remove('deferred');
          elem.removeAttribute('data-deferred');
        } else {
          var img = document.createElement('img');
          img.src = data.thumbnail;
          elem.parentNode.replaceChild(img, elem);
        }
      }
    }
  });

  // Subscribe to the thumbnail ready event.
  for (var i = 0; i < deferred.length; i++) {
    var data_deferred = deferred[i].getAttribute('data-deferred');
    if (data_deferred) {
      socket.emit('deferred', {target: data_deferred});
    }
  }
}


u.ready(function () {
  loadLazy();
  subscribeDeferred();
})

socket.on('notification', function(d){
  updateNotifications(d.count.messages + d.count.notifications);
  updateTitleNotifications();
});

socket.on('mod-notification', function(d) {
  var found = false;
  for (var i=0; i < modData.length; i++) {
    if (modData[i][0] == d.update[0]) {
      modData[i][1] = d.update[1];
      found = true;
    }
  }
  if (!found){
    modData.push(d.update);
  }
  updateModNotifications(modData);
  updateTitleNotifications();
})

socket.on('uinfo', function(d){
  updateNotifications(d.ntf);
  modData = d.mod_ntf;
  updateModNotifications(modData);
  updateTitleNotifications();
  document.getElementById('postscore').innerHTML = d.taken;
});

socket.on('uscore', function(d){
  document.getElementById('postscore').innerHTML = d.score;
})

socket.on('deletion', function(data){
  var post = document.querySelector('div.post[pid="' + data.pid + '"]');
  post.parentNode.removeChild(post);
})

socket.on('comment', function(data){
  const recentActivity = document.getElementById('activity_list');
  if(recentActivity){
    const content = data.title.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    const elem = document.createElement('li');
    elem.innerHTML = _('%1 commented "%2" in %3 %4', '<a href="/u/' + data.user + '">' + data.user + '</a>', '<a href="' + data.post_url + '">' + content + '</a>', '<a href="' + data.sub_url + '">' + data.sub_url + '</a>', '<time-ago datetime="' + new Date().toISOString() + '" class="sidebarlists"></time-ago>')
    recentActivity.prepend(elem);
  }
});

socket.on('thread', function(data){
  if(window.blocked){
    if(window.blocked.indexOf(data.sid) >= 0){return;}
  }
  const recentActivity = document.getElementById('activity_list');
  const title = data.title.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
  if(recentActivity){
    const elem = document.createElement('li');
    elem.innerHTML = _('%1 posted "%2" to %3 %4', '<a href="/u/' + data.user + '">' + data.user + '</a>', '<a href="' + data.post_url + '">' + title + '</a>', '<a href="' + data.sub_url + '">' + data.sub_url + '</a>', '<time-ago datetime="' + new Date().toISOString() + '" class="sidebarlists"></time-ago>')
    recentActivity.prepend(elem);
    return;
  }
  const recentActivitySidebar = document.getElementById('activity_list_sidebar');
  if(recentActivitySidebar && data.show_sidebar){
    const elem = document.createElement('li');
    let html = _('%1 posted: %2', '<a href="/u/' + data.user + '">' + data.user + '</a>', '<a class="title" href="' + data.post_url + '">' + title + '</a>');
    html += '<div class="sidelocale">' +
              _("%1 in %2", '<time-ago datetime="' + new Date().toISOString() + '"></time-ago>', '<a href="' + data.sub_url + '">' + data.sub_url + '</a>') +
            '</div>';
    elem.innerHTML = html;
    recentActivitySidebar.prepend(elem);
    recentActivitySidebar.removeChild(recentActivitySidebar.lastChild);
  }
  socket.emit('subscribe', {target: data.pid})
  const ndata = document.createElement("div");
  ndata.innerHTML = data.html;
  const x = document.getElementsByClassName('alldaposts')[0];

  while (ndata.firstChild) {
    const k = x.insertBefore(ndata.firstChild, x.children[0]);
    if(window.expandall && k.getElementsByClassName){
      const q = k.getElementsByClassName('expando-btn')[0];
      if(q && q.getAttribute('data-icon') == "image"){
        q.click()
      }
    }

  }
  loadLazy();
  subscribeDeferred();
  icon.rendericons();
})

socket.on('threadscore', function(data){
  console.log('article#' + data.pid + ' .count')
  document.querySelector('div[pid="' + data.pid + '"] .score').innerHTML = data.score;
})

socket.on('threadcomments', function(data){
  console.log('article#' + data.pid + ' .ccount')
  document.querySelector('div[pid="' + data.pid + '"] .comments').innerHTML = _('comments (%1)', data.comments);
})

socket.on('threadtitle', function(data){
  document.querySelector('div[pid="' + data.pid + '"] .title').innerHTML = data.title;
});

socket.on('yourvote', function(data){
  var th = document.querySelector('div.post[pid="' + data.pid + '"] .votebuttons')
  if(th){
    if(data.status == -1){
      th.querySelector('.upvote').classList.remove('upvoted');
      th.querySelector('.downvote').classList.add('downvoted');
    }else if(data.status == 1){
      th.querySelector('.upvote').classList.add('upvoted');
      th.querySelector('.downvote').classList.remove('downvoted');
    }else{
      th.querySelector('.upvote').classList.remove('upvoted');
      th.querySelector('.downvote').classList.remove('downvoted');
    }
    th.querySelector('.score').innerHTML = data.score;
  }
})

u.ready(function () {
  socket.on('connect', function () {
    if (document.getElementById('chpop') && window.chat == true) {
      socket.emit('subscribe', {target: 'chat'});
    }
  });
  socket.on('connect', function () {
    window.sio = true;
    if (window.nposts) {
      socket.emit('subscribe', {target: window.nposts});
    }
    if(document.getElementById('activity_list')) {
      socket.emit('subscribe', {target: '/all/new'});
    }
    u.each('div.post', function (t) {
      socket.emit('subscribe', {target: parseInt(t.getAttribute('pid'))});
    })
  });
})

u.sub('#chsend', 'keydown', function(e){
  if(document.getElementById('matrix-chat')) return
  if(e.keyCode == 13){
    socket.emit('msg', {msg: this.value})
    this.value = '';
    var x = document.getElementById('chcont');
    x.scrollTop = x.scrollHeight
  }
})

var ircStylize = require("irc-style-parser");

socket.on('rmannouncement', function(){
  if(window.oindex){
    document.getElementById('announcement-post').outerHTML = '';
  }
})

socket.on('msg', function(data){
  if(document.getElementById('matrix-chat')) return
  var cont = document.getElementById('chcont')
  if(!cont){return;}
  var uname = document.getElementById('unameb').innerHTML.toLowerCase();
  var reg = /(^|\s)(@|\/u\/)([a-zA-Z0-9_-]{3,})(\s|\'|\.|,|$)/g
  var reg2 = /\u0001ACTION (.+)\u0001/
  var m = data.msg.match(reg);
  var m2 = data.msg.match(reg2);
  var xc="";
  if(m && !m[3]){m[3] = '';}
  if(m && m[3].toLowerCase() == uname && data.user.toLowerCase() != uname){
    xc="msg-hl";
    // TODO: Ping sounds here?
  }
  if(m2){
    data.msg = data.user + ' ' + m2[1];
    data.user = "*";
    xc=xc + " msg-ac";
  }
  cont.innerHTML = cont.innerHTML + '<div class="msg ' + xc + '"><span class="msguser">' + data.user + '&gt;</span><span class="damsg">' + anchorme(ircStylize(data.msg.replace(/  /g, '&#32;&nbsp;')), {emails: false, files: false, attributes: [{name:"target",value:"blank"}]}).replace(reg, "$1<a href='/u/$3'>$2$3</a>$4") + '</span></div>';
  var k = document.getElementsByClassName('msg')
  if(k.length > 3){
    if(u.isScrolledIntoView(k[k.length-2])){
      k[k.length-2].scrollIntoView();
    }
  }
})

socket.on('announcement', function(data){
  if(window.oindex){
    var elm = document.createElement('div');
    elm.id = "announcement-post";
    elm.innerHTML = data.cont;
    document.getElementById('container').insertAdjacentElement('afterbegin', elm);
    icon.rendericons();
  }
})

export default socket;
