var socket = io.connect('//' + document.domain + ':' + location.port + '/alt');
var md = new showdown.Converter({tables: true, extensions: ['xssfilter']});
var user = {};  // user info


var menu_home = {  // the menu for home_*
  oninit: function () {},
  view: function (ctrl) {
    return [m('li.pure-menu-item', {active: (m.route.get() == '/' || m.route.get() == '/hot') ? true : false}, m('a.pure-menu-link[href="/hot"]', {oncreate: m.route.link},'Hot')),
            m('li.pure-menu-item', {active: (m.route.get() == '/new') ? true : false}, m('a.pure-menu-link[href="/new"]', {oncreate: m.route.link},'New')),
            m('li.pure-menu-item', m('a.pure-menu-link[href="/all/new"]', {oncreate: m.route.link}, 'Recent'))];
  }
};

var menu_all = {  // the menu for all_*
  oninit: function () {},
  view: function (ctrl) {
    return [m('li.pure-menu-item', m('span', m('b', 'All'))),
						m('li.pure-menu-item', {active: (m.route.get() == '/all/hot') ? true : false}, m('a.pure-menu-link[href="/all/hot"]', {oncreate: m.route.link},'Hot')),
            m('li.pure-menu-item', {active: (m.route.get() == '/all/top') ? true : false}, m('a.pure-menu-link[href="/all/top"]', {oncreate: m.route.link},'Top')),
            m('li.pure-menu-item', {active: (m.route.get() == '/all/new') ? true : false}, m('a.pure-menu-link[href="/all/new"]', {oncreate: m.route.link}, 'New'))];
  }
};

var menu_sub = {  // the menu for sub_*
  oninit: function () {return {sub: m.route.param("sub")};},
  view: function (c) {
    if (current_sub.name) {
      switch(m.route.get()) {
        case '/s/' + c.sub:
          ep = current_sub.sort;
          break;
        case '/s/' + c.sub + '/hot':
          ep = 'hot'; break;
        case '/s/' + c.sub + '/new':
          ep = 'new'; break;
        case '/s/' + c.sub + '/top':
          ep = 'top'; break;
        default:
          ep = '';
      }
      return [m('li.pure-menu-item', m('span', m('a.bold', {href: '/s/' + current_sub.name, oncreate: m.route.link}, current_sub.name))),
  						m('li.pure-menu-item', {active: (ep == 'hot') ? true : false}, m('a.pure-menu-link', {href: '/s/' + current_sub.name + '/hot', oncreate: m.route.link},'Hot')),
              m('li.pure-menu-item', {active: (ep == 'top') ? true : false}, m('a.pure-menu-link', {href: '/s/' + current_sub.name + '/top', oncreate: m.route.link},'Top')),
              m('li.pure-menu-item', {active: (ep == 'new') ? true : false}, m('a.pure-menu-link', {href: '/s/' + current_sub.name + '/new', oncreate: m.route.link}, 'New'))];
    }
  }
};


var menu_user = {  // the menu for user_*
  oninit: function (vnode) {return {user: m.route.param("user")};},
  view: function (ctrl) {
      return [m('li.pure-menu-item', m('span', m('b', m.route.param("user")))),
              m('li.pure-menu-item', {}, m('a.pure-menu-link', {href: '/u/' + m.route.param("user") + '/posts', oncreate: m.route.link},'Posts')),
              m('li.pure-menu-item', {}, m('a.pure-menu-link', {href: '/u/' + m.route.param("user") + '/comments', oncreate: m.route.link},'Comments'))];
              // m('li.pure-menu-item', {}, m('a.pure-menu-link', {href: '/u/' + m.route.param("user") + '/saved', config: m.route}, 'Saved'))];
  }
};

m.route.prefix("#");

/* routing */
m.routes('/', {// default route
    /* Frontpage */
    '/': {'#th-main': home_hot, '#th-menu': menu_home},
    '/all/hot': {'#th-main': all_hot, '#th-menu': menu_all},
    '/all/new': {'#th-main': all_new, '#th-menu': menu_all},
    '/all/top': {'#th-main': all_top, '#th-menu': menu_all},
    '/top': {'#th-main': home_top, '#th-menu': menu_home},
    '/new': {'#th-main': home_new, '#th-menu': menu_home},
    '/hot': {'#th-main': home_hot, '#th-menu': menu_home},
    /* Frontpage page numbers */
    '/all/hot/:page': {'#th-main': all_hot, '#th-menu': menu_all},
    '/all/new/:page': {'#th-main': all_new, '#th-menu': menu_all},
    '/all/top/:page': {'#th-main': all_top, '#th-menu': menu_all},
    '/top/:page': {'#th-main': home_top, '#th-menu': menu_home},
    '/new/:page': {'#th-main': home_new, '#th-menu': menu_home},
    '/hot/:page': {'#th-main': home_hot, '#th-menu': menu_home},

    /* User */
    '/login': {'#th-main': login},
    '/register': {'#th-main': register},
    '/u/:user': {'#th-main': view_user, '#th-menu': menu_user},
    '/u/:user/posts': {'#th-main': view_user_posts, '#th-menu': menu_user},
    // TODO '/u/:user/comments': {'#th-main': view_user_comments, '#th-menu': menu_user},
    // TODO '/u/:user/saved': {'#th-main': view_user_saved, '#th-menu': menu_user},
    /* User page numbers */
    '/u/:user/posts/:page': {'#th-main': view_user_posts, '#th-menu': menu_user},
    // TODO '/u/:user/comments/:page': {'#th-main': view_user_comments, '#th-menu': menu_user},
    // TODO '/u/:user/saved/:page': {'#th-main': view_user_saved, '#th-menu': menu_user},

    /* Sub */
    '/s/:sub': {'#th-main': sub_auto, '#th-menu': menu_sub},
    '/s/:sub/hot': {'#th-main': sub_hot, '#th-menu': menu_sub},
    '/s/:sub/top': {'#th-main': sub_top, '#th-menu': menu_sub},
    '/s/:sub/new': {'#th-main': sub_new, '#th-menu': menu_sub},
    /* Sub page numbers */
    '/s/:sub/hot/:page': {'#th-main': sub_hot, '#th-menu': menu_sub},
    '/s/:sub/top/:page': {'#th-main': sub_top, '#th-menu': menu_sub},
    '/s/:sub/new/:page': {'#th-main': sub_new, '#th-menu': menu_sub},

    /* domain page */
    // TODO '/domain/:domain': {'#th-main': sub_hot},

    /* Post */
    '/s/:sub/:pid': {'#th-main': view_post, '#th-menu': menu_sub}
  });

/* User view thingy controller */
var user = {};
user.udata = {};
user.oninit = function(vx){
  var state = this;
  state.logout = function() {
    m.request({
      method: "POST",
      url: "/do/logout",
      data: {j: true, csrf_token: document.getElementById('csrf_token').value}
    });
  };
  state.listen = function() {
    socket.on("uinfo", function (data) {
      state.udata = data;
      m.redraw();
    });
  }();
};

user.view = function (ctrl){  // login thingy
  var u = this.udata;
	if(u.loggedin === undefined) {
		return m("div.cw-items", 'Loading...');
	}
  return m("div.cw-items", {}, function(){
          if (u.loggedin){
                return [m('a', {href: '/u/' + u.name, class: 'smallcaps', oncreate: m.route.link}, u.name),
                m('span', {class: 'separator'}),
                m('abbr', {title: 'Phuks taken', class: 'bold'}, u.taken),
                m('span', {class: 'separator'}),
                m('abbr', {title: 'Phuks given'}, u.given),
                m('span', {class: 'separator'}),
                m('a', {class: 'glyphbutton sep', href: '#'},
                  m('i', {class: 'fa fa-sliders', title: 'Settings'})),
                m('a', {class: 'glyphbutton sep'},
                  m('i', {class: 'fa ' + function(){
                                  if (u.ntf === 0){
                                    return 'fa-envelope-o';
                                  }else{
                                    return 'fa-envelope hasmail';
                                  }
                                }(), title: 'Messages'})),
                m('a', {class: 'glyphbutton', id: 'toggledark'},
                  m('i', {class: 'fa fa-lightbulb-o', title: 'Toggle light mode', onclick: toggle_darkmode})),
                m('span', {class: 'separator'}),
                m('a[href="#"]', {onclick: ctrl.logout}, 'Log out')];
          }else{
            return [m('a[href="/login"]', {oncreate: m.route.link}, 'Log in'),
                    m('span.separator'),
                    m('a[href="/register"]', {oncreate: m.route.link}, 'Register')];
          }
        }()
      );
};

var subar = {};
subar.oninit = function (vx) {
	var ctrl = this;
	m.request({
		method: 'GET',
		url: '/api/v1/getSubscriptions'
	}).then(function(res) {
      ctrl.subs = res.subscriptions;
  });
};
subar.view = function (ctrl){ // sub bar
	x = [];
	for( var i in this.subs ){
		x.push(m('li.subinthebar', m('a', {oncreate: m.route.link, href: '/s/' + this.subs[i]}, this.subs[i].toUpperCase())));
	}
	return x;
};

m.mount(
    document.getElementById('th-uinfo'), user
);
m.mount(
    document.getElementById('th-subar'), subar
);
