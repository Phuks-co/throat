import io from 'socket.io-client';
import icon from './Icon'
import u from './Util';

const socket = io('//' + window.wsserver + '/snt', {transports: ['websocket'], upgrade: false});
socket.on('notification', function(d){
  // bahhh
  var title = document.getElementsByTagName('title')[0].innerHTML.split('\n');
  title = title[title.length-1]
  if(d.count == 0){
    document.title = '\n' + title;
    document.getElementById('mailcount').innerHTML = '';
    document.getElementById('mailcount').style.display = 'none';
  }else{
    document.title = '(' + d.count + ')\n ' + title;
    document.getElementById('mailcount').innerHTML = d.count;
    document.getElementById('mailcount').style.display = 'inline-block';
  }
})
socket.on('uscore', function(d){
  document.getElementById('postscore').innerHTML = d.score;
})

socket.on('thread', function(data){
  socket.emit('subscribe', {target: data.pid})
  document.getElementsByClassName('alldaposts')[0].innerHTML = data.html + document.getElementsByClassName('alldaposts')[0].innerHTML;
  icon.rendericons();
})

socket.on('threadscore', function(data){
  console.log('article#' + data.pid + ' .count')
  document.querySelector('div[pid="' + data.pid + '"] .score').innerHTML = data.score;
})

socket.on('threadcomments', function(data){
  console.log('article#' + data.pid + ' .ccount')
  document.querySelector('div[pid="' + data.pid + '"] .comments').innerHTML = 'comments (' + data.comments + ')';
})
u.ready(function(){
  if(window.labrat){
    socket.on('connect', function() {
      window.sio = true;
      if(window.nposts){
        socket.emit('subscribe', {target: window.nposts});
      }
      u.each('div.post', function(t, i){
        socket.emit('subscribe', {target: parseInt(t.getAttribute('pid'))});
      })
    });
  }
})


u.sub('#chtitle', 'click', function(e){
  var hid = this.getAttribute('hid');
  if(!hid){ // hid
    this.parentNode.style.height = '1.65em';
    document.getElementById('chbott').style.display='none';
    this.setAttribute('hid', true);
  }else{
    this.parentNode.style.height = '50%';
    document.getElementById('chbott').style.display='block';
    this.removeAttribute('hid');
  }
})

function isScrolledIntoView(el) {
    var elemTop = el.getBoundingClientRect().top;
    var elemBottom = el.getBoundingClientRect().bottom;
    var isVisible = (elemTop >= 0) && (elemBottom <= window.innerHeight);
    return isVisible;
}

u.sub('#chsend', 'keydown', function(e){
  if(e.keyCode == 13){
    socket.emit('msg', {msg: this.value})
    this.value = '';
    var x = document.getElementById('chcont');
    x.scrollTop = x.scrollHeight
  }
})

socket.on('msg', function(data){
  var cont = document.getElementById('chcont')
  cont.innerHTML = cont.innerHTML + '<div class="msg"><span class="msguser">' + data.user + '&gt;</span><span class="damsg">' + data.msg + '</span></div>';
  var k = document.getElementsByClassName('msg')
  if(k.length > 3){
    if(isScrolledIntoView(k[k.length-2])){
      k[k.length-2].scrollIntoView();
    }
  }
})


module.exports = socket;
