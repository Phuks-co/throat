import './ext/CustomElements.min.js';
import 'purecss/build/base.css';
import 'purecss/build/forms.css';
import 'purecss/build/buttons.css';
import 'purecss/build/grids.css';
import 'purecss/build/grids-responsive.css';
import 'time-elements/time-elements.js';
import u from './Util';
import Konami from './ext/konami';

require('../css/main.css');
require('../css/dark.css');

var icons = require('./Icon');
require('./Expando');
require('./Post');
require('./Editor');
require('./Messages');
require('./Sub');
var socket = require('./Socket');


function vote(obj, how, comment){
  console.log(how)
  if(comment){
    var kl = 'votecomment';
    var unid = obj.parentNode.parentNode.parentNode.getAttribute('data-cid');
    var count = obj.parentNode.parentNode.querySelector('.cscore');
  } else {
    var kl = 'vote';
    var unid = obj.getAttribute('data-pid');
    var count = obj.parentNode.querySelector('.score');
  }
  u.post('/do/' + kl + '/'+ unid + '/' + how, {}, function(data){
    console.log(data)
    if(data.status == "ok"){
      console.log(obj);
      obj.classList.add((how == 'up') ? 'upvoted' : 'downvoted');
      if(obj.parentNode.querySelector((how == 'up') ? '.downvoted' : '.upvoted')){
        obj.parentNode.querySelector((how == 'up') ? '.downvoted' : '.upvoted').classList.remove((how == 'up') ? 'downvoted' : 'upvoted')
      }
      count.innerHTML = data.score;
    }
  }, function(err){
    //TODO: show errors
  })
}

// up/downvote buttons.
u.addEventForChild(document, 'click', '.upvote,.downvote,.c-upvote,.c-downvote', function(e, target){
  var upvote = (target.classList.contains('upvote') || target.classList.contains('c-upvote'))
  var comment = (target.classList.contains('c-upvote') || target.classList.contains('c-downvote'))
  vote(target, upvote ? 'up':'down', comment)
})


u.ready(function() {
  // shitless forms
  u.addEventForChild(document, 'submit', '.ajaxform', function(e, target){
    e.preventDefault();
    var button = target.querySelector("[type=submit]");
    var btnorm = button.innerHTML;
    var data = new FormData(target);

    button.setAttribute('disabled', true);
    if(button.getAttribute('data-prog')){
      button.innerHTML = button.getAttribute('data-prog');
    }
    u.rawpost(target.getAttribute('action'), data,
      function(data){ // success
        if (data.status != "ok") {
          button.removeAttribute('disabled');
          var obj = data.error, q = data.error.length,
            ul = document.createElement('ul'); // >_>
          for (var i = 0; i < q; i++) {
            ul.innerHTML = ul.innerHTML + "<li>" + obj[i] + "</li>";
          }
          if(target.querySelector('.div-error')){
            target.querySelector('.div-error').innerHTML = '<span class="closebtn" onclick="this.parentElement.style.display=\'none\';">&times;</span>' +
                    '<ul>' + ul.innerHTML + '</ul>';
            target.querySelector('.div-error').style.display = 'block';
          }
          button.innerHTML = btnorm;
          if (typeof grecaptcha != "undefined") {
              grecaptcha.reset();
          }
        } else { // success
          if(target.getAttribute('data-reset')){
            target.reset();
          }
          if(button.getAttribute('data-success')){
            button.innerHTML = button.getAttribute('data-success');
          }
          if(target.getAttribute('data-redir')){
            if(target.getAttribute('data-redir') == "true"){
              document.location = data.addr;
            }else{
              document.location = target.getAttribute('data-redir');
            }
          }else if (target.getAttribute('data-reload')) {
            console.log('tried');
            document.location.reload();
          }else{
            button.removeAttribute('disabled');
          }
        }
      }, function() { //error
        target.querySelector('.div-error').innerHTML = '<span class="closebtn" onclick="this.parentElement.style.display=\'none\';">&times;</span> <p><ul><li>Error while contacting the server</li></ul></p>';
        target.querySelector('.div-error').style.display = 'block';
        button.removeAttribute('disabled');
        button.innerHTML = btnorm;
      })
  });
});

// toggle dark mode
if(document.getElementById('toggledark')){
  document.getElementById('toggledark').addEventListener('click', function(){
    var mode = getCookie("dayNight");
    var d = new Date();
    d.setTime(d.getTime() + (365 * 24 * 60 * 60 * 1000)); //365 days
    var expires = "expires=" + d.toGMTString();
    if (mode == "dark" || mode == "dank") {
      document.cookie = "dayNight" + "=" + "light" + "; " + expires + ";path=/";
      document.getElementsByTagName('body')[0].classList.remove('dark');
      document.getElementsByTagName('body')[0].classList.remove('dank');
      document.querySelector('#toggledark span').innerHTML = icons.moon;
      //document.getElementById('chpop').style.display='none'
    } else {
      document.cookie = "dayNight" + "=" + "dark" + "; " + expires + ";path=/";
      document.getElementsByTagName('body')[0].classList.add('dark');
      document.querySelector('#toggledark span').innerHTML = icons.sun;
    }
  })
}
// TODO: move to util
function getCookie(cname) {
    var name = cname + "=";
    var ca = document.cookie.split(';');
    for (var i = 0; i < ca.length; i++) {
        var c = ca[i];
        while (c.charAt(0) == ' ') {
            c = c.substring(1);
        }
        if (c.indexOf(name) === 0) {
            return c.substring(name.length, c.length);
        }
    }
    return "";
}
if(document.getElementById('delete_account')){
  document.getElementById('delete_account').addEventListener('click', function(e){
    if(document.getElementById('delete_account').checked){
      if(!confirm('Are you sure you want to PERMANENTLY delete your account?')){
        e.preventDefault()
        return false;
      }
    }
  })
}


// admin - remove banned domain
if(document.querySelector('button.removebanneddomain')){
  document.querySelector('button.removebanneddomain').addEventListener('click', function(){
    var domain=this.getAttribute('data-domain');
    u.post('/do/remove_banned_domain/' + domain, {}, function(data){
      if (data.status == "ok") {
        document.location.reload();
      }
    })
  });
}


/* purecss*/
var menu = document.getElementById('menu'),
    WINDOW_CHANGE_EVENT = ('onorientationchange' in window) ? 'orientationchange':'resize';

function toggleHorizontal() {
    [].forEach.call(
        document.getElementById('menu').querySelectorAll('.can-transform'),
        function(el){
            el.classList.toggle('pure-menu-horizontal');
        }
    );
};

function toggleMenu() {
    // set timeout so that the panel has a chance to roll up
    // before the menu switches states
    if (menu.classList.contains('open')) {
        setTimeout(toggleHorizontal, 500);
    }
    else {
        toggleHorizontal();
    }
    menu.classList.toggle('open');
    document.getElementById('toggle').classList.toggle('x');
};

function closeMenu() {
    if (menu.classList.contains('open')) {
        toggleMenu();
    }
}

document.getElementById('toggle').addEventListener('click', function (e) {
    toggleMenu();
    e.preventDefault();
});

window.addEventListener(WINDOW_CHANGE_EVENT, closeMenu);

/* infinite scroll */
u.ready(function(){
  var mode = getCookie("dayNight");
  //if(mode == 'dank'){
    socket.emit('subscribe', {target: 'chat'});
  //}

if(window.moreuri){
  window.loading = false;
  window.addEventListener('scroll', function () {
      if(window.loading){
        return
      }
      if(window.scrollY + window.innerHeight >= (document.getElementsByTagName('body')[0].clientHeight/100)*75) {
          var k = document.querySelectorAll('div.post')
          var lastpid = k[k.length-1].getAttribute('pid')
          window.loading = true;
          u.get(window.moreuri + lastpid,
            function(data) {
              var ndata = document.createElement( "div" );
              ndata.innerHTML = data;

              while (ndata.firstChild) {
                  document.querySelector('.alldaposts').appendChild(ndata.firstChild);
              }

              window.loading = false;
              icons.rendericons();
            })
      }
  });
}
})

new Konami(function() {
  var d = new Date();
  d.setTime(d.getTime() + (365 * 24 * 60 * 60 * 1000)); //365 days
  var expires = "expires=" + d.toGMTString();
  socket.emit('subscribe', {target: 'chat'});
  document.getElementById('chpop').style.display='block'
    document.cookie = "dayNight" + "=" + "dank" + "; " + expires + ";path=/";
    document.getElementsByTagName('body')[0].classList.add('dark');
    document.getElementsByTagName('body')[0].classList.add('dank');
    document.querySelector('#toggledark span').innerHTML = icons.sun;
});


window.onbeforeunload = function (e) {
  var flag = false;
  u.each('.exalert', function(e){
    if(e.value !== ''){
      flag = true;
    }
  })
  if(flag && !window.sending){
    return 'Sure?';
  }
};

u.addEventForChild(document, 'click', '#postcontent a,.commblock .content a', function(e, qelem){
  var uri = qelem.getAttribute('href');
  var m = qelem.parentNode.querySelector('img[src="' + uri + '"]');
  if(uri.match(/\.(jpg|png|gif|jpeg)$/i)){
    e.preventDefault();
    if(!m){
      var nn = document.createElement('img');
      nn.src = uri;
      nn.classList.add('alimg');
      qelem.parentNode.insertBefore(nn, qelem.nextSibling);
    }else{
      m.parentNode.removeChild(m);
    }
  }
})

u.addEventForChild(document, 'click', 'img.alimg', function(e, qelem){
  qelem.parentNode.removeChild(qelem);
})
