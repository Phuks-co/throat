/* Misc functions go here */

/* Little hack so we can operate various modules with one route */
m.routes = function mRoutes( defaultRoute, routesMap ){
	var routes = {};

	for( var route in routesMap ){
		routes[ route ] = {
			oninit : subRouter( routesMap[ route ] ),
			view       : noop
		};
	}

	return m.route( document.querySelector( '.footer' ), defaultRoute, routes );

	function subRouter( modules ){
		return function routeChange(l){
					l.redraw = true;
					l.skip = false;

          for( var key in modules ){
              m.mount(document.querySelector( key ), modules[ key ]);
          }
        };
	}

	function noop(){}
};

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


function get_hostname(url) {
  if(!url){return;}
  var matches = url.match(/^https?\:\/\/([^\/?#]+)(?:[\/?#]|$)/i);
  return matches[1];
}
function vimeoID(url) {
  var match = url.match(/https?:\/\/(?:www\.)?vimeo.com\/(?:channels\/(?:\w+\/)?|groups\/([^\/]*)\/videos\/|album\/(\d+)\/video\/|)(\d+)(?:$|\/|\?)/);
  if (match){
    return match[3];
	}
}
function vineID(url) {
  var match = url.match(/^http(?:s?):\/\/(?:www\.)?vine\.co\/v\/([a-zA-Z0-9]{1,13})$/);
  if (match){
    return match[1];
	}
}
function gfycatID(url) {
  var match = url.match(/^http(?:s?):\/\/gfycat\.com\/([a-zA-Z0-9]{1,60})$/);
  if (match){
    return match[1];
	}
}
function youtubeID(url) {
  var match =  url.match(/^.*(youtu\.be\/|v\/|u\/\w\/|embed\/|watch\?v=|\&v=)([^#\&\?]*).*/);
  if (match && match[2].length == 11) {
    return match[2];
  }
}
function imgurID(url) {
  var match = url.match(/^http(?:s?):\/\/(i\.)?imgur\.com\/(.*?)(?:\/.gifv|$)/);
  if (match){
    return match[2].replace(/.gifv/,'');
	}
}
function xkcdID(url) {
  var match = url.match(/^http(?:s?):\/\/xkcd\.com\/([a-zA-Z0-9/]{1,10})$/);
  if (match){
    return match[1].replace(/\//,'');
	}
}
function streamableID(url) {
  var match = url.match(/^http(?:s?):\/\/streamable\.com\/([a-zA-Z0-9]{1,10})$/);
	if (match){
	 return match[1];
	}
}
function codepenID(url) {
  var match = url.match(/^http(?:s?):\/\/codepen\.io\/([a-zA-Z0-9]{1,20})\/pen\/([a-zA-Z0-9/]{1,20})$/);
  if (match){
    return match[1];
	}
}
function codepenUSER(url) {
	var match = url.match(/^http(?:s?):\/\/codepen\.io\/([a-zA-Z0-9]{1,20})\/pen\/([a-zA-Z0-9/]{1,20})$/);
  if (match){
    return match[2].replace(/\//,'');
	}
}


/* static mithril module for the logo */
var lm = {};
var logo = document.getElementById('kxlogo').innerHTML;
lm.view = function () {
	return [m("a.pure-menu-heading[href='/']", {oncreate: m.route.link},[
						m('span#kxlogo', m.trust(logo))
						//m("img[alt='Throat'][id='logo'][src='/static/img/logo-white.svg']")
				 ])];
};
m.mount(document.getElementById('LogoMenu'), lm);


/* Menu */
(function (window, document) {
  var menu = document.getElementById('menu'),
    WINDOW_CHANGE_EVENT = ('onorientationchange' in window) ? 'orientationchange':'resize';

  function toggleHorizontal() {
    [].forEach.call(
      document.getElementById('menu').querySelectorAll('.custom-can-transform'),
      function(el){
        //el.classList.toggle('pure-menu-horizontal');
      }
    );
  }

  function toggleMenu() {
    // set timeout so that the panel has a chance to roll up
    // before the menu switches states
    if (menu.classList.contains('open')) {
      setTimeout(toggleHorizontal, 500);
    }else {
      toggleHorizontal();
    }
    menu.classList.toggle('open');
    document.getElementById('toggle').classList.toggle('x');
  }

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

})(this, this.document);


/* Duh. Toggles dark mode */
function toggle_darkmode () {
	l = document.getElementsByTagName('body')[0].classList;
	l.toggle('dark');
	var mode = getCookie("dayNight");
	var d = new Date();
	d.setTime(d.getTime() + (365 * 24 * 60 * 60 * 1000)); //365 days
	var expires = "expires=" + d.toGMTString();
	document.cookie = "dayNight=" + ((l.value == 'dark')?'dark' : 'light') + "; " + expires + ";path=/";
}
