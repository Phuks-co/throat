var socket = io.connect('//' + document.domain + ':' + location.port + '/alt');
var md = converter = new showdown.Converter({tables: true, extensions: ['xssfilter']});
var user = {}  // user info


var menu_home = {  // the menu for home_*
  controller: function () {},
  view: function (ctrl) {
    return [m('li.pure-menu-item', {active: (m.route() == '/' || m.route() == '/hot') ? true : false}, m('a.pure-menu-link[href="/all/hot"]', {config: m.route},'Hot')),
            m('li.pure-menu-item', {active: (m.route() == '/new') ? true : false}, m('a.pure-menu-link[href="/new"]', {config: m.route},'New')),
            m('li.pure-menu-item', m('a.pure-menu-link[href="/all/new"]', {config: m.route}, 'Recent'))]
  }
};

var menu_all = {  // the menu for all_*
  controller: function () {},
  view: function (ctrl) {
    return [m('li.pure-menu-item', m('span', m('b', 'All'))),
						m('li.pure-menu-item', {active: (m.route() == '/all/hot') ? true : false}, m('a.pure-menu-link[href="/all/hot"]', {config: m.route},'Hot')),
            m('li.pure-menu-item', {active: (m.route() == '/all/top') ? true : false}, m('a.pure-menu-link[href="/all/top"]', {config: m.route},'Top')),
            m('li.pure-menu-item', {active: (m.route() == '/all/new') ? true : false}, m('a.pure-menu-link[href="/all/new"]', {config: m.route}, 'New'))]
  }
};


m.route.mode = "hash";

/* routing */
m.routes('/', {// default route
    '/': {'#th-main': home_hot, '#th-menu': menu_home},
    '/all/hot': {'#th-main': all_hot, '#th-menu': menu_all},
    '/all/new': {'#th-main': all_new, '#th-menu': menu_all},
    '/all/top': {'#th-main': all_top, '#th-menu': menu_all},
    '/top': {'#th-main': home_top, '#th-menu': menu_home},
    '/new': {'#th-main': home_new, '#th-menu': menu_home},
    '/hot': {'#th-main': home_hot, '#th-menu': menu_home},
    '/login': {'#th-main': login},
    '/register': {'#th-main': register}
  })

/* User view thingy controller */
var user = {};
user.udata = {};
user.vm = new function () {
  var vm = {};
  vm.init = function () {
    vm.logout = function() {
      m.request({
        method: "POST",
        url: "/do/logout",
        data: {j: true, csrf_token: document.getElementById('csrf_token').value}
      });
    };
    vm.listen = (function() {
      m.startComputation();
      socket.on("uinfo", function (data) {
        user.udata = data;
        m.endComputation();
      });
    })();
  };
  return vm;
};

user.controller = function(){
  user.vm.init();
};

function toggle_darkmode () {
	l = document.getElementsByTagName('body')[0].classList
	l.toggle('dark');
	var mode = getCookie("dayNight");
	var d = new Date();
	d.setTime(d.getTime() + (365 * 24 * 60 * 60 * 1000)); //365 days
	var expires = "expires=" + d.toGMTString();
	document.cookie = "dayNight=" + ((l.value == 'dark')?'dark' : 'light') + "; " + expires + ";path=/";
}

user.view = function (ctrl){  // login thingy
  var u = user.udata;
	if(u.loggedin == undefined) {
		return m("div.cw-items", 'Loading...');
	}
  return m("div.cw-items", {}, function(){
          if (u.loggedin){
                return [m('a', {href: '/u/' + u.name, class: 'smallcaps'}, u.name),
                m('span', {class: 'separator'}),
                m('abbr', {title: 'Phuks taken', class: 'bold'}, u.taken),
                m('span', {class: 'separator'}),
                m('abbr', {title: 'Phuks given'}, u.given),
                m('span', {class: 'separator'}),
                m('a', {class: 'glyphbutton sep', href: '#'},
                  m('i', {class: 'fa fa-sliders', title: 'Settings'})),
                m('a', {class: 'glyphbutton sep'},
                  m('i', {class: 'fa ' + function(){
                                  if (u.ntf == 0){
                                    return 'fa-envelope-o';
                                  }else{
                                    return 'fa-envelope hasmail';
                                  }
                                }(), title: 'Messages'})),
                m('a', {class: 'glyphbutton', id: 'toggledark'},
                  m('i', {class: 'fa fa-lightbulb-o', title: 'Toggle light mode', onclick: toggle_darkmode})),
                m('span', {class: 'separator'}),
                m('a[href="#"]', {onclick: user.vm.logout}, 'Log out')]
          }else{
            return [m('a[href="/login"]', {config: m.route}, 'Log in'),
                    m('span.separator'),
                    m('a[href="/register"]', {config: m.route}, 'Register')]
          }
        }()
      )
};

var subar = {};
subar.controller = function () {
	var ctrl = {};
	m.request({
		method: 'GET',
		url: '/do/get_subscriptions'
	}).then(function(res) {
			ctrl.subs = res.subscriptions;
			m.endComputation();
	});
	return ctrl;
};
subar.view = function (ctrl){ // sub bar
	x = [];
	for( var i in ctrl.subs ){
		x.push(m('li.subinthebar', m('a', {config: m.route, href: '/s/' + ctrl.subs[i]}, ctrl.subs[i].toUpperCase())))
	}
	return x;
};

m.module(document.getElementById('th-uinfo'), {controller: user.controller, view: user.view});
m.module(document.getElementById('th-subar'), {controller: subar.controller, view: subar.view});
var lm = {};
var logo = document.getElementById('kxlogo').innerHTML;
lm.view = function () {
	return [m("a.pure-menu-heading[href='/']", {config: m.route},[
						m('span#kxlogo', {config: function (element, isInit, context){
							context.retain = true;
							if (!isInit && logo != undefined) {
								document.getElementById('kxlogo').innerHTML = logo;
							}
						}})
						//m("img[alt='Throat'][id='logo'][src='/static/img/logo-white.svg']")
				 ])]
};
m.module(document.getElementById('LogoMenu'), {view: lm.view});

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
  };

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
  };

  function closeMenu() {
    if (menu.classList.contains('open')) {
      toggleMenu();
    }
  };

  document.getElementById('toggle').addEventListener('click', function (e) {
    toggleMenu();
    e.preventDefault();
  });

  window.addEventListener(WINDOW_CHANGE_EVENT, closeMenu);

})(this, this.document);
