import './ext/CustomElements.min.js';
import 'purecss/build/base.css';
import 'purecss/build/forms.css';
import 'purecss/build/buttons.css';
import 'purecss/build/grids.css';
import 'purecss/build/grids-responsive.css';
import 'purecss/build/menus.css';
import 'tingle.js/dist/tingle.css';
import 'time-elements';
//import 'flatpickr/dist/flatpickr.css';
import 'flatpickr/dist/themes/dark.css';

import u from './Util';
import Konami from './ext/konami';
import Sortable from 'sortablejs';
import flatpickr from "flatpickr";
import Tingle from 'tingle.js';
import _ from './utils/I18n';

window.Sortable = Sortable;
require('../css/main.css');
require('../css/dark.css');
require('../css/custom.css');

import icons from './Icon';
require('./Expando');
require('./Post');
require('./Editor');
require('./Messages');
require('./Sub');
require('./Poll');
require('./Mod');
require('./Badge');
require('./Chat');

import socket from './Socket'

function vote(obj, how, comment){
  // Check if we're logged in first
  if(!document.getElementById('logout')){
    // Show modal offering login or registration.
    var modal = new Tingle.modal({});

    modal.setContent('<h2>' + _('Log in or register to continue') + '</h2>\
    <div class="pure-g"> \
      <div class="pure-u-1-1 pure-u-lg-1-2">\
        <h3> Log in </h3> \
        <form method="POST" action="/login?next=' + encodeURI(window.location.pathname) + '" class="pure-form pure-form-aligned">\
          <input type="hidden" name="csrf_token" value="' + document.getElementById('csrf_token').value + '"/> \
          <fieldset> \
            <div class="pure-control-group"> \
              <input id="username" name="username" pattern="[a-zA-Z0-9_-]+" placeholder="' + _('Username') + '" required="" title="' + _('Alphanumeric characters plus \'-\' and \'_\'') + '" type="text"> \
            </div> \
            <div class="pure-control-group"> \
              <input id="password" name="password" placeholder="' + _('Password') + '" required type="password"> \
            </div> \
            <div class="pure-controls">\
              <label for="remember" class="pure-checkbox">\
              <input id="remember" name="remember" type="checkbox" value="y"> ' + _('Remember me') + ' \
              </label> \
              <button type="submit" class="pure-button pure-button-primary">' + _('Log in') + '</button> \
            </div> \
            <br/> \
            <div> \
              <a href="/recover">' + _('Forgot your password?') + '</a>\
            </div> \
          </fieldset> \
        </form> \
      </div> \
      <div class="pure-u-1-1 pure-u-lg-1-2"> \
      <h3>Register</h3> \
      <p>' + _('Don\'t have an account?') + '</p> \
      <a class="pure-button pure-button-primary" href="/register">' + _('Register now!') + '</a>\
      </div> \
    </div> \
    ');
    modal.open();
    return;
  }

  if(comment){
    var kl = 'votecomment';
    var unid = obj.parentNode.parentNode.parentNode.getAttribute('data-cid');
    var count = obj.parentNode.parentNode.querySelector('.cscore');
  } else {
    var kl = 'vote';
    var unid = obj.getAttribute('data-pid');
    var count = obj.parentNode.querySelector('.score');
  }
  if (!obj.getAttribute('data-in-progress')) {
    obj.setAttribute('data-in-progress', true);
    u.post('/do/' + kl + '/'+ unid + '/' + how, {}, function(data){
      obj.removeAttribute('data-in-progress');
      console.log(obj.classList)
      if(!data.rm){
        obj.classList.add((how == 'up') ? 'upvoted' : 'downvoted');
        if(obj.parentNode.querySelector((how == 'up') ? '.downvoted' : '.upvoted')){
          obj.parentNode.querySelector((how == 'up') ? '.downvoted' : '.upvoted').classList.remove((how == 'up') ? 'downvoted' : 'upvoted')
        }
      }else{
        obj.classList.remove((how == 'up') ? 'upvoted' : 'downvoted');
      }
      count.innerHTML = data.score;
    }, function(err){
      obj.removeAttribute('data-in-progress');
      //TODO: show errors
    })
  }
}

// up/downvote buttons.
u.addEventForChild(document, 'mousedown', '.upvote,.downvote,.c-upvote,.c-downvote', function(e, target){
  var upvote = (target.classList.contains('upvote') || target.classList.contains('c-upvote'))
  var comment = (target.classList.contains('c-upvote') || target.classList.contains('c-downvote'))
  vote(target, upvote ? 'up':'down', comment)
  e.preventDefault();
})


u.ready(function() {
  u.addEventForChild(document, 'change', 'input[type="file"]', function(e, target){
    if (!window.FileReader) return;

    var input = target
    if (!input.files) {
        return;
    }
    else if (!input.files[0]) {
        return;
    }else {
        var file = input.files[0];
        var max = target.getAttribute('data-max');
        if( max && file.size > max){
          alert(_("File size exceeds maximum allowed (%1 MB)", max / 1024 / 1024))
          target.value = '';
        }
    }
  })
  // initialize all date pickers
  flatpickr(".date-picker-future", {
    enableTime: true,
    dateFormat: 'Z',
    altInput: true,
    altFormat: 'Y-m-d H:i',
    time_24hr: true,
  });
  // Hide the Submit a post poll flatpickr initially.
  var cb = document.getElementById('closetime_date');
  if (cb && cb.nextElementSibling) {
    cb.nextElementSibling.style.display = 'none';
  }

  // for the top bar sorts
  var list = document.getElementById("subsort");
  if(list){
    new window.Sortable(list, {
      animation: 100,
    });
  }

  u.sub('.save-top_bar', 'click', function(e){
    var btn = this;
    btn.setAttribute('disabled', true);
    btn.innerHTML = _("Saving...");
    var subs = []
    u.each('.subsort_item', function(e){
      subs.push(e.getAttribute('sid'))
    });
    u.post('/do/edit_top_bar', {sids: subs}, function(d){
      if (d.status == "ok") {

      }else{
        alert(_('There was an error while saving your settings. Please try again in a few minutes.'));
      }
      btn.removeAttribute('disabled');
      btn.innerHTML = _("Save");
    }, function(){
      alert(_('There was an error while saving your settings. Please try again in a few minutes.'));
      btn.removeAttribute('disabled');
      btn.innerHTML = _("Save");
    })
  })

    document.querySelectorAll(".ajaxform").forEach((element)=> {
        element.onSubmit = (event, target) => {
            event.preventDefault();
            console.log(event);
        };
    });

  // TODO: Get rid of this.
  u.addEventForChild(document, 'submit', '.ajaxform', function(e, target){
    e.preventDefault();
    // The SubmitEvent API isn’t supported in Safari, so work around it.
    var button = e.submitter || target.querySelector("[type=submit]");
    var btnorm = button.innerHTML;
    var data = new FormData(target);

    button.setAttribute('disabled', true);
    if(button.getAttribute('data-prog')){
      button.innerHTML = button.getAttribute('data-prog');
    }
    let action = target.getAttribute('action')
    if (e.submitter && e.submitter.getAttribute("formaction")) {
      action = e.submitter.getAttribute("formaction");
    }
    u.rawpost(action, data,
      function(data){ // success
        if (data.status != "ok") {
          button.removeAttribute('disabled');
          let error = data.error;
          if(Array.isArray(data.error)){
            error = data.error[0];
          }
          if(target.querySelector('.div-error')){
            target.querySelector('.div-error').innerHTML = error;
            target.querySelector('.div-error').style.display = 'block';
          }
          if(target.querySelector('.div-message')){
            target.querySelector('.div-message').style.display = 'none';
          }
          button.innerHTML = btnorm;
        } else { // success
          let message = data.message;
          if(Array.isArray(data.message)){
            message = data.message[0];
          }
          if(target.querySelector('.div-message')){
            target.querySelector('.div-message').innerHTML = message;
            if (message) {
                target.querySelector('.div-message').style.display = 'block';
            } else {
                target.querySelector('.div-message').style.display = 'none';
            }
          }
          if(target.querySelector('.div-error')){
            target.querySelector('.div-error').style.display = 'none';
          }

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
            document.location.reload();
          }else{
            button.removeAttribute('disabled');
          }
        }
      }, function(data) { //error
        let error = _('Error while contacting the server');
        if(data.startsWith('{')){
          let jsdata = JSON.parse(data);
          error = data.error;
          if(Array.isArray(jsdata.error)){
            error = jsdata.error[0];
          }
        }
        if(target.querySelector('.div-error')) {
          target.querySelector('.div-error').innerHTML = error;
          target.querySelector('.div-error').style.display = 'block';
        }
        button.removeAttribute('disabled');
        button.innerHTML = btnorm;
      })
  });

    // Tag buttons with delete for a confirmation
    Array(...document.getElementsByClassName("delete")).forEach(element => {
        if(element.type !== "submit"){
            return;
        }
        element.onclick = (event) => {
            return confirm(_("Are you sure you want to delete?"));
        };
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
      if(!confirm(_('Are you sure you want to PERMANENTLY delete your account?'))){
        e.preventDefault()
        return false;
      }
    }
  })
}


// admin - remove banned domain
if(document.querySelector('button.removebanneddomain')){
  u.addEventForChild(document, 'click', 'button.removebanneddomain', function(e, qelem){
    var domain=qelem.getAttribute('data-domain');
    var domain_type=qelem.getAttribute('data-domain-type')
    u.post('/do/remove_banned_domain/' + domain_type + '/' + domain, {}, function(data){
      if (data.status == "ok") {
        document.location.reload();
      }
    })
  });
}


/* purecss*/
var menu = document.getElementById('menu'),
    WINDOW_CHANGE_EVENT = ('onorientationchange' in window) ? 'orientationchange':'resize';
    /* var sidebar = document.getElementById('sidebar'); */

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
  /*  sidebar.classList.toggle('open') */
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

u.ready(function(){
  // "More" dropdown
  u.sub('.dropdown-toggle.moremenu', 'click', function(e){
    var hsubs = document.getElementById('hiddensubs');
    if(hsubs.style.display != 'none' && hsubs.style.display){
      hsubs.style.display = 'none';
      console.log('noned')
      return
    }
    var w = document.querySelector('.th-subbar ul').clientWidth
    var x = ''
    u.each('#topbar li', function(e){
      var p = {left: e.offsetLeft, top: e.offsetTop};
      var pl = p.left + e.clientWidth;
      if (pl < 0 - (e.clientWidth-30) || pl > w){
        x = x + '<li>' + e.innerHTML + '</li>'
      }
     });
     document.getElementById('hiddensubs').innerHTML = x;
     hsubs.style.display = 'inline-flex';

     var lastChild = hsubs.children[hsubs.children.length-1];
     var newWidth = lastChild.offsetLeft + lastChild.offsetWidth + 15;
     hsubs.style.width = newWidth + 'px';
 });
 u.addEventForChild(document, 'click', '*', function(e, qelem){
   var hsubs = document.getElementById('hiddensubs');
   var hdrop = document.querySelector('.dropdown-toggle.moremenu');
  if(hsubs.style.display != 'none' && hsubs.style.display){
    // i hate this.
    if(qelem != hsubs && qelem.parentNode != hsubs && qelem != hdrop && qelem != hdrop.parentNode && qelem.parentNode != hdrop && qelem.parentNode.parentNode != hdrop && qelem.parentNode.parentNode.parentNode != hdrop){
      console.log(qelem, hsubs)
      hsubs.style.display = 'none';
    }
  }
 })
  // Sort by menu
  u.sub('.sortmenu', 'click', function(e){
    var sortby = document.getElementById('sortby');
    if (sortby.style.display != 'none' && sortby.style.display){
      sortby.style.display = 'none';
      return
    }
     sortby.style.display = 'inline-flex';
  });
  // chat
  if(document.getElementById('chcont')){
    socket.emit('subscribe', {target: 'chat'});
    socket.emit('getchatbacklog');
  }

  /* infinite scroll */
  window.moreuri = document.getElementById("pagefoot-moreuri");
  window.page = 1;
  window.loading = false;
  if(window.moreuri){
    window.moreuri = window.moreuri.getAttribute('data-value');
    window.addEventListener('scroll', function () {
      if(window.loading){return;}
      if(window.scrollY + window.innerHeight >= (document.getElementsByTagName('body')[0].clientHeight/100)*75) {
        window.page++;
        var k = document.querySelectorAll('div.post')
        var lastpid = k[k.length-1].getAttribute('pid')
        window.loading = true;
        u.get(window.moreuri + '/' + window.page + '/' + lastpid,
        function(data) {
          var ndata = document.createElement( "div" );
          ndata.innerHTML = data;

          while (ndata.firstChild) {
            var k = document.querySelector('.alldaposts').appendChild(ndata.firstChild);
            if(window.expandall && k.getElementsByClassName){
              var q = k.getElementsByClassName('expando-btn')[0]
              if(q && q.getAttribute('data-icon') == "image"){
                q.click()
              }
            }
          }

          window.loading = false;
          icons.rendericons();
          socket.loadLazy();
        })
      }
    });
  }

  window.addEventListener('scroll', function () {
    if(window.loading){return;}
    if(window.scrollY + window.innerHeight >= (document.getElementsByTagName('body')[0].clientHeight/100)*75) {
      const sibload = document.querySelector(".comments a.loadsibling[data-pcid='']");
      if(sibload) {
        sibload.click();
      }
    }
  });

  // Spoiler tags
  u.addEventForChild(document, 'click', 'spoiler', function(e, target) {
    target.classList.add("shown");
  });
})

u.ready(function(){
  u.each('*[data-timefmt]', function(el,i) {
    var fmt = el.getAttribute('data-timefmt');
    if (el.innerHTML == 'None') {
      el.innerHTML = _("Never");
    } else {
      var d = new Date(el.innerHTML);
      if (fmt == 'datetime') {
        el.innerHTML = d.toISOString().replace(/T/, ' ').replace(/\..+/, '');
      }
    }
  })
});

new Konami(function() {
  var d = new Date();
  d.setTime(d.getTime() + (365 * 24 * 60 * 60 * 1000)); //365 days
  var expires = "expires=" + d.toGMTString();
  if(document.getElementById('chpop')) document.getElementById('chpop').style.display='block'
  document.cookie = "dayNight" + "=" + "dank" + "; " + expires + ";path=/";
  document.getElementsByTagName('body')[0].classList.add('dark');
  document.getElementsByTagName('body')[0].classList.add('dank');
  document.querySelector('#toggledark span').innerHTML = icons.sun;
});

u.ready(function () {
  if (document.getElementById("throat-chat")) {
    window.chat = "true";
  }

  if (document.getElementById("pagefoot-oindex")) {
    window.oindex = "true";
  }

  if (document.getElementById("pagefoot-labrat")) {
    window.blocked = document.getElementById("pagefoot-blocked");
    if (window.blocked) {
      window.blocked = window.blocked.getAttribute('data-value');
      console.log("Blocked=", window.blocked)
      window.nposts = '/all/new';
    }
  }

  u.addEventForChild(document, 'click', '#btn-sending', function(e, target) {
    window.sending = true;
  })

  u.addEventForChild(document, 'click', '#banuser-button', function(e, target) {
    if (confirm(_('Are you sure you want to ban this user?'))) {
      document.getElementById('banuser').submit();
    }
  })
  u.addEventForChild(document, 'click', '#wipevotes-button', function(e, target) {
    if (confirm(_('Are you sure you want to remove all the votes issued by this user?'))) {
      document.getElementById('wipevotes').submit();
    }
  })
  u.addEventForChild(document, 'click', '#unbanuser-button', function(e, target) {
    if (confirm(_('Are you sure you want to unban this user?'))) {
      document.getElementById('unbanuser').submit();
    }
  })
})


window.onbeforeunload = function (e) {
  var flag = false;

  u.each('.exalert', function(e){
    if(e.value !== ''){
      flag = true;
    }
  })
  if(e.target.activeElement.tagName == 'INPUT') flag = false;
  if(flag && !window.sending){
    return 'Sure?';
  }
};


u.addEventForChild(document, 'click', 'img.alimg', function(e, qelem){
  qelem.parentNode.removeChild(qelem);
})

/* sub banner href */
if (typeof(document.getElementsByClassName("subinfo")[0]) != 'undefined' && document.getElementsByClassName("subinfo")[0] != null){
  //left side
  var link = document.getElementsByClassName("subinfo")[0].children[0].children[0].getAttribute("href");
  var text = document.getElementsByClassName("subinfo")[0].children[0].children[0].innerText;
  var bannerLink = document.getElementsByClassName("banner-link")[0];
  bannerLink.setAttribute("href", link);
  bannerLink.style.position = "absolute";
  bannerLink.style.top = "0px";
  bannerLink.style.left = "0px";
  bannerLink.style.width = "100%";
  bannerLink.style.height = "100%";
  document.getElementsByClassName("cw-brand")[0].style.zIndex = "10";
  //add text link
  var a = document.createElement('a');
  var linkText = document.createTextNode(text);
  a.appendChild(linkText);
  a.title = text;
  a.href = link;
  a.className = "banner-text-link";
  document.getElementById("menu").appendChild(a);
}

/* load all comments on a post */
if (typeof(document.getElementById("cmnts")) != 'undefined' && document.getElementById("cmnts") != null){
  if (typeof(document.getElementById("cmnts").children[0]) != 'undefined' && document.getElementById("cmnts").children[0] != null){
      document.getElementById("cmnts").children[0].addEventListener('click', function(event){   
        event.preventDefault();
        var self = this;
        var interval = setInterval(function(){
            var comments = document.getElementsByClassName("loadsibling");
            if(comments.length == 0){
                clearInterval(interval);
                interval = false;
            }
            for(var i = 0;i<comments.length;i++){
                comments[i].click();
            }
        },300); 
        return false;    
      });
  }
}  

//topbar active page link indication
var activePage = window.location.pathname.split("/").slice(0,3).join("/");
if("/all/hot" == activePage)
   activePage = "/all";   
var childs = document.getElementById("topbar").children;
for(var i = 0;i<childs.length;i++){
    if( childs[i].firstElementChild){
        if(childs[i].firstElementChild.nodeName == "A"){
            var nodeLink = childs[i].firstElementChild.getAttribute("href").split("/").slice(0,3).join("/");
            if(nodeLink == activePage){
                 childs[i].firstElementChild.classList.add("active-page-link"); 
                 childs[i].firstElementChild.style.color = '#c90511';
            }
        }
    }
}

u.addEventForChild(document, 'click', '.nsfw-blur', function(e, qelem){
  e.preventDefault();
  qelem.classList.remove('nsfw-blur');
})


u.addEventForChild(document, 'click', '.block-blur', function(e, qelem){
  e.preventDefault();
  qelem.classList.remove('block-blur');
})


// User blocks and ignores.
// Show the Save changes button when any change is made to the select inputs.
u.addEventForChild(document, 'input', '.ignore-form-select', function(e, qelem){
  const uid = qelem.id.substring("ign-msg-".length);
  const saveButton = document.getElementById('submit-ignore-' + uid);
  saveButton.classList.remove('hide');
  saveButton.innerHTML = _('Save changes')
})
