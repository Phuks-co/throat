import './ext/CustomElements.min.js';
import 'purecss/build/base.css';
import 'purecss/build/forms.css';
import 'purecss/build/buttons.css';
import 'purecss/build/grids.css';
import 'purecss/build/grids-responsive.css';
import 'purecss/build/tables.css';
import 'time-elements/time-elements.js';
import $ from 'jquery';
import u from './Util';

require('../css/main.css');
require('../css/dark.css');

var icons = require('./Icon');
require('./Expando');
require('./Post');
require('./Editor');
require('./Messages');
require('./Sub');


function vote(obj, how, comment){
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
      obj.parentNode.querySelector((how == 'up') ? '.downvoted' : '.upvoted').classList.remove((how == 'up') ? 'downvoted' : 'upvoted')
      count.innerHTML = (how == 'up') ? (parseInt(count.innerHTML)+1) : (parseInt(count.innerHTML)-1)
    }
  }, function(err){
    //TODO: show errors
  })
}

// up/downvote buttons.
u.addEventForChild(document, 'click', '.upvote,.downvote,.c-upvote,.c-downvote', function(e, target){
  vote(target, target.className.endsWith('upvote') ? 'up' : 'down', target.className.startsWith('c-'))
})

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
