import './ext/CustomElements.min.js';
import 'purecss/build/base.css';
import 'purecss/build/forms.css';
import 'purecss/build/buttons.css';
import 'purecss/build/grids.css';
import 'purecss/build/grids-responsive.css';
import 'purecss/build/tables.css';
import 'time-elements/time-elements.js';
import $ from 'jquery';

require('../css/main.css');
require('../css/dark.css');

var icons = require('./Icon');
require('./Expando');
require('./Post');
require('./Editor');
require('./Messages');
require('./Sub');
require('./Socket');


function vote(obj, how, comment){
  if(comment){
    var kl = 'votecomment';
    var unid = obj.parent().parent().parent().data('cid');
    var count = obj.parent().parent().children('.cscore');
  } else {
    var kl = 'vote';
    var unid = obj.data('pid');
    var count = obj.parent().children('.score');
  }
  $.ajax({
    type: "POST",
    url: '/do/' + kl + '/'+ unid + '/' + how,
    data: {csrf_token: $('#csrf_token')[0].value},
    dataType: 'json',
    success: function(data) {
      console.log(data)
      if(data.status == "ok"){
        console.log(obj)
        obj.addClass((how == 'up') ? 'upvoted' : 'downvoted');
        obj.parent().children((how == 'up') ? '.downvoted' : '.upvoted').removeClass((how == 'up') ? 'downvoted' : 'upvoted');

        count.text(data.score);
      }
    }
  }).catch(function(e){
    if(e.status == 403){
      // TODO: Show error if user is not authenticated
    }
  });
}

// up/downvote buttons.
$(document).on('click', '.upvote', function(){
  var obj = $(this);
  vote(obj, 'up');
});

$(document).on('click', '.downvote', function(){
  var obj = $(this);
  console.log(obj)
  vote(obj, 'down');
});

$(document).on('click', '.c-upvote', function(){
  var obj = $(this);
  vote(obj, 'up', true);
});

$(document).on('click', '.c-downvote', function(){
  var obj = $(this);
  vote(obj, 'down', true);
});

$(document).ready(function() {
  // shitless forms
  $(document).on('submit', ".ajaxform", function(e){
    e.preventDefault();
    var target = $(e.target);
    var button = $(target.find("[type=submit]")[0]);
    var btnorm = button.text();
    button.prop('disabled', true);
    button.text(button.data('prog'));
    $.ajax({
      type: "POST",
      dataType: 'json',
      url: target.prop('action'),
      data: target.serialize(),
      success: function(data) {
        if (data.status != "ok") {
          button.prop('disabled', false);
          var obj = data.error,
            ul = $("<ul>"); // >_>
          for (var i = 0, l = obj.length; i < l; ++i) {
            ul.append("<li>" + obj[i] + "</li>");
          }
          target.find('.div-error').html('<span class="closebtn" onclick="this.parentElement.style.display=\'none\';">&times;</span>' +
                        '<ul>' + ul.html() + '</ul>');
          target.find('.div-error').show();
          button.text(btnorm);
          if (typeof grecaptcha != "undefined") {
              grecaptcha.reset();
          }
        } else { // success
          if(target.data('reset')){
            target[0].reset();
          }
          if(button.data('success')){
            button.text(button.data('success'));
          }
          if(target.data('redir')){
            if(target.data('redir') === true){
              document.location = data.addr;
            }else{
              document.location = target.data('redir');
            }
          }else if (target.data('reload')) {
            console.log('tried');
            document.location.reload();
          }else{
            button.prop('disabled', false);
          }
        }
      },
      error: function(data, err) {
        target.find('.div-error').html('<span class="closebtn" onclick="this.parentElement.style.display=\'none\';">&times;</span> <p><ul><li>Error while contacting the server</li></ul></p>');
        target.find('.div-error').show();
        button.prop('disabled', false);
        button.text(btnorm);
      }
    });
    console.log(target.data());
  });
});

// toggle dark mode
$("#toggledark").click(function() {
  var mode = getCookie("dayNight");
  var d = new Date();
  d.setTime(d.getTime() + (365 * 24 * 60 * 60 * 1000)); //365 days
  var expires = "expires=" + d.toGMTString();
  if (mode == "dark") {
    document.cookie = "dayNight" + "=" + "light" + "; " + expires + ";path=/";
    $("body").removeClass("dark");
    $('#toggledark span').html(icons.moon);
  } else {
    document.cookie = "dayNight" + "=" + "dark" + "; " + expires + ";path=/";
    $("body").addClass("dark");
    $('#toggledark span').html(icons.sun);
  }
});

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
$('button.removebanneddomain').click(function(){
  var domain=$(this).data('domain')
  $.ajax({
    type: "POST",
    url: '/do/remove_banned_domain/' + domain,
    dataType: 'json',
    success: function(data) {
        if (data.status == "ok") {
          document.location.reload();
        }
    }
  });
});


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
