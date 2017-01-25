var socket = io.connect('//' + document.domain + ':' + location.port + '/alt');
var md = converter = new showdown.Converter({tables: true, extensions: ['xssfilter']});
var user = {}  // user info
/* Little hack so we can operate various modules with one route */
m.routes = function mRoutes( defaultRoute, routesMap ){
	var routes = {};

	for( var route in routesMap ){
		routes[ route ] = {
			controller : subRouter( routesMap[ route ] ),
			view       : noop
		};
	}

	return m.route( document.body, defaultRoute, routes );

	function subRouter( modules ){
		return function routeChange(){
			m.redraw.strategy( 'none' );

			for( var key in modules ){
				m.module( document.querySelector( key ), modules[ key ] );
			}
		};
	}

	function noop(){}
};



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

function postWrapper(post) {
  var post = post;
  post.domain = get_hostname(post.link);
  post.close_expando = function () {
    m.startComputation();
    post.expando = false;
    m.endComputation();
  }
  post.youtube_expando = function () {
    var id = youtubeID(post.link);
    if (id) {
      m.startComputation();
      post.expando = m('div.pure-g', m('div.pure-u-1.pure-u-md-3-24'), m('div.pure-u-1.pure-u-md-13-24', m('div.iframewrapper',
                      m('iframe', {width: '100%', src: 'https://www.youtube.com/embed/' + id})
                    )));
      m.endComputation();
    }
  };
  post.gfycat_expando = function () {
    var id = gfycatID(post.link);
    if (id) {
      m.startComputation();
      post.expando = m('div.pure-g', m('div.pure-u-1.pure-u-md-3-24'), m('div.pure-u-1.pure-u-md-13-24', m('div.iframewrapper',
                      m('iframe', {width: '100%', src: 'https://gfycat.com/ifr/' + id})
                    )));
      m.endComputation();
    }
  };
  post.vine_expando = function () {
    var id = vineID(post.link)
    if (id) {
      m.startComputation();
      post.expando = m('div.pure-g', m('div.pure-u-1.pure-u-md-3-24'), m('div.pure-u-1.pure-u-md-13-24', m('div.iframewrapper',
                      m('iframe', {width: '100%', src: 'https://vine.co/v/' + id + '/embed/simple'})
                    )));
      m.endComputation();
    }
  };
  post.vimeo_expando = function () {
    var id = vimeoID(post.link)
    if (id) {
      m.startComputation();
      post.expando = m('div.pure-g', m('div.pure-u-1.pure-u-md-3-24'), m('div.pure-u-1.pure-u-md-13-24', m('div.iframewrapper',
                      m('iframe', {width: '100%', src: 'https://player.vimeo.com/video/' + id})
                    )));
      m.endComputation();
    }
  };
  post.image_expando = function () {
    m.startComputation();
    post.expando = m('div.pure-g', m('div.pure-u-1.pure-u-md-3-24'), m('div.pure-u-1.pure-u-md-13-24',
                    m('img', {src: post.link, onclick: post.close_expando})
                  ));
    m.endComputation();
  };
  post.video_expando = function () {
    m.startComputation();
    post.expando = m('div.pure-g', m('div.pure-u-1.pure-u-md-3-24'), m('div.pure-u-1.pure-u-md-13-24',
                    m('video', {preload: 'auto', autoplay: 'autoplay', loop: 'loop', controls: true},
                      m('source', {src: post.link})
                    )
                  ));
    m.endComputation();
  };
  post.imgur_gifv_expando = function () {
    m.startComputation();
    post.expando = m('div.pure-g', m('div.pure-u-1.pure-u-md-3-24'), m('div.pure-u-1.pure-u-md-13-24',
                    m('video', {preload: 'auto', autoplay: 'autoplay', loop: 'loop'},
                      m('source', {src: 'https://i.imgur.com/' + imgurID(post.link) + '.mp4'})
                    )
                  ));
    m.endComputation();
  };
  post.tweet_expando = function () {
    m.startComputation();
    post.expando = m('div.pure-g', m('div.pure-u-1.pure-u-md-3-24'), m('div.pure-u-1.pure-u-md-13-24', m('div.iframewrapper',
                    m('iframe', {width: '100%', src: 'https://twitframe.com/show?url=' + post.link})
                  )));
    m.endComputation();
  };

  post.text_expando = function () {
    m.startComputation();
    m.request({
      method: 'GET',
      url: '/do/get_post_md/' + post.pid
    }).then(function(res) {
        if (res.status == 'ok'){
          post.expando = m('div.pure-g', m('div.pure-u-1.pure-u-md-3-24'), m('div.pure-u-1.pure-u-md-13-24',
                          m('span', m.trust(md.makeHtml(res.content)))
                        ));
        }
        m.endComputation();
    });
  };
  return post;
}
function renderPosts(posts){
  var l = posts.length;
  var tffs = [];
  for (var i = 0; i < l; ++i) {
    post = postWrapper(posts[i])
    tffs.push(m('div.post.pure-g', {pid: post['pid']},
               m('div.pure-u-8-24.pure-u-md-4-24.misctainer',
                m('div.votebuttons.pure-u-1-24.pure-u-md-1-24',
                  m('div.fa.fa-chevron-up.upvote', {class: (post.vote == 1) ? 'upvoted' : '', title: 'Upvote'}),
                  m('div.score', post.score),
                  m('div.fa.fa-chevron-down.downvote', {class: (post.vote == 0) ? 'downvoted' : '', title: 'Downvote'})
                ), // UV/DV/score
                m('div.thcontainer',
                function(){
                    return m('div.thumbnail', {}, function () {
                              if (post.thumbnail != '' && post.ptype == 1){
                                return m('img', {src: thumbs + post.thumbnail})
                              }else if(post.ptype == 1){
                                return m('span.placeholder',
                                          m('i.fa.fa-link.fa-inverse')
                                        );
                              }else{
                                return m('span.placeholder',
                                         m('i.fa.fa-comments.fa-inverse')
                                        );
                              }
                          }())
                }(), m('span.pure-badge', m('i.fa.fa-comments'), ' ', post.comments)) // thumbnail
               ),
                m('div.pure-u-16-24.pure-u-md-20-24.pbody',
									m('div.post-heading',
	                  function () {
	                    if (post.ptype == 0){
	                      return m('a.title[href=/s/' + post['sub']['name'] + '/' + post['pid'] + ']', {}, post['title']);
	                    } else {
	                      return [m('a.title', {href: post['link']}, post['title']),
	                              m('span.domain', ' (', m('a[href=#]', {}, post.domain), ')')
	                              ];
	                    }
	                  }()),
                  m('div.author',
                    function () {
                      if(post.expando){
                        return m('div.expando', {onclick: post.close_expando}, m('i.fa.fa-close'));
                      }else{
                        if (post.ptype == 1){
                          if ((post.domain == 'youtube.com') || (post.domain == 'www.youtube.com') || (post.domain == 'youtu.be')) {
                            return m('div.expando', {onclick: post.youtube_expando}, m('i.fa.fa-youtube-play'));
                          }else if (post.domain == 'gfycat.com') {
                            return m('div.expando', {onclick: post.gfycat_expando}, m('i.fa.fa-play'));
                          }else if (post.domain == 'vine.co') {
                            return m('div.expando', {onclick: post.vine_expando}, m('i.fa.fa-vine'));
                          }else if (post.domain == 'vimeo.com') {
                            return m('div.expando', {onclick: post.vimeo_expando}, m('i.fa.fa-vimeo'));
                          }else if(/\.(png|jpg|gif|tiff|svg|bmp|jpeg)$/i.test(post.link)) {
                            return m('div.expando', {onclick: post.image_expando}, m('i.fa.fa-image'));
                          }else if (/\.(mp4|webm)$/i.test(post.link)) {
                            return m('div.expando', {onclick: post.video_expando}, m('i.fa.fa-play'));
                          }else if (post.domain == 'i.imgur.com' && /\.gifv$/i.test(post.link)) {
                            return m('div.expando', {onclick: post.imgur_gifv_expando}, m('i.fa.fa-play'));
                          }else if (post.domain == 'twitter.com') {
                            return m('div.expando', {onclick: post.tweet_expando}, m('i.fa.fa-twitter'));
                          }
                        } else { // text post
                          if (post.content) {
                            return m('div.expando', {onclick: post.text_expando}, m('i.fa.fa-file-text-o'));
                          }
                        }
                      }
                    }(),'posted ',
                    m('time-ago', {datetime: post.posted}),
                    ' by ', (post.username == '[Deleted]') ? '[Deleted]' : m('a', {href: '/u/'+ post.username, config: m.route}, post.username),
                    ' on ', m('a', {href: '/s/' + post.sub.name, config: m.route}, post.sub.name)
                  )
                )
              ),
              function () {
                if(post.expando){
                  return post.expando;
                }
              }());
  }
  return tffs;
}

var all_hot = {}; // all_hot is the base for all the other sorters!
all_hot.control = function (type, sort){
  var ctrl = this;
  ctrl.err = '';
  ctrl.posts = [];
  ctrl.get_posts = function () {
    m.startComputation();
    window.stop();  // We're going to change pages, so cancel all requests.
    m.request({
      method: 'GET',
      url: '/do/get_frontpage/' + type + '/' + sort
    }).then(function(res) {
        if (res.status == 'ok'){
          ctrl.posts = res.posts;
        } else {
          ctrl.err = res.error
        }
        m.endComputation();
    }).catch(function(err) {
      ctrl.err = [err];
      m.endComputation();
    });
  };
  m.redraw();
  ctrl.get_posts();
  return ctrl;
};
all_hot.controller = function() {return all_hot.control('all', 'hot')};
all_hot.view = function (ctrl) {
  if (ctrl.err != ''){
    return m('div.content.pure-u-1', {}, "Error loading posts: " + ctrl.err);
  }else {
    if (!ctrl.posts.length) {

      return [m('div.content.pure-u-1 pure-u-md-18-24', {}, 'Loading...'),
              m('div.sidebar.pure-u-1 pure-u-md-6-24')];
    } else {
      return [m('div.content.pure-u-1 pure-u-md-18-24', {}, renderPosts(ctrl.posts)),
              m('div.sidebar.pure-u-1 pure-u-md-6-24')];
    }
  }
};

var all_new = {
  controller: function (){ return all_hot.control('all', 'new'); },
  view: function(ctrl) { return all_hot.view(ctrl); }
};

var all_top = {
  controller: function (){ return all_hot.control('all', 'top'); },
  view: function(ctrl) { return all_hot.view(ctrl); }
};

var home_hot = {
  controller: function (){ return all_hot.control('home', 'hot'); },
  view: function(ctrl) { return all_hot.view(ctrl); }
};

var home_new = {
  controller: function (){ return all_hot.control('home', 'new'); },
  view: function(ctrl) { return all_hot.view(ctrl); }
};


var home_top = {
  controller: function (){ return all_hot.control('home', 'top'); },
  view: function(ctrl) { return all_hot.view(ctrl); }
};

var login = {
  controller: function () {
    var ctrl = this;
    ctrl.user = {
      username: '',
      password: '',
      csrf_token: document.getElementById('csrf_token').value
    };
    ctrl.err = '';
    ctrl.success = '';
    ctrl.login = function (e) {
      e.preventDefault();
      m.request({
        method: 'POST',
        url: '/do/login',
        data: ctrl.user
      }).then(function(res) {
          if (res.status == 'ok'){
            m.route('/');
            ctrl.success = 'Logged in!';
          } else {
            ctrl.err = res.error
          }
      }).catch(function(err) {
        ctrl.err = [err];
      });
    };
  },
  view: function (ctrl) {
    return m('div.content.pure-u-1', {},
              m('div.form', {onsubmit: ctrl.login},
                m('form.pure-form.pure-form-aligned',
                  m('fieldset',
                    m('div.pure-control-group',
                      m('label', {for: 'username'}, 'Username'),
                      m('input#username[type="text"]', {
                                  placeholder: 'Username',
                                  value: ctrl.user.username,
                                  onchange: function(e) {
                                    ctrl.user.username = e.currentTarget.value;
                                  }})
                    ),
                    m('div.pure-control-group',
                      m('label', {for: 'password'}, 'Password'),
                      m('input#password[type="password"]', {
                                  placeholder: 'Password',
                                  value: ctrl.user.password,
                                  onchange: function(e) {
                                    ctrl.user.password = e.currentTarget.value;
                                  }})
                    ),
                    m('div.pure-controls',
                      m('button.pure-button.pure-button-primary[type="submit"]', 'Log in')
                    ),
                    (ctrl.success) ? m('.success', ctrl.success) : '',
                    (ctrl.err) ? m('.error', ctrl.err.map(function (lm,i) {return m('span', lm);})) : ''
                  )
                )
              )
           );
  }
};



var register = {
  controller: function () {
    var ctrl = this;
    var recaptcha = document.createElement('script');
    recaptcha.setAttribute('src', 'https://www.google.com/recaptcha/api.js?onload=CaptchaCallback&render=explicit');
    recaptcha.setAttribute('async', true);
    recaptcha.setAttribute('defer', true);
    recaptcha.setAttribute('onload', "javascript:document.getElementById('g-recaptcha').innerHTML = ''");
    document.head.appendChild(recaptcha);

    ctrl.user = {
      username: '',
      email: '',
      password: '',
      confirm: '',
      invitecode: '',
      accept_tos: '',
      'g-recaptcha-response': '',
      csrf_token: document.getElementById('csrf_token').value
    };
    ctrl.icode = false;
    ctrl.icodecheck = (function() {
      m.startComputation();
      socket.emit('register', {})
      socket.on("rsettings", function (data) {
        ctrl.icode = data.icode;
        m.endComputation();
      });
    })();
    ctrl.err = '';
    ctrl.success = '';
    ctrl.register = function (e) {
      e.preventDefault();
      ctrl.user['g-recaptcha-response'] = document.getElementById('g-recaptcha-response').value;
      m.request({
        method: 'POST',
        url: '/do/register',
        data: ctrl.user
      }).then(function(res) {
          if (res.status == 'ok'){
            m.route('/');
            ctrl.success = 'Registered!';
          } else {
            ctrl.err = res.error
          }
      }).catch(function(err) {
        ctrl.err = [err];
      });
    };
  },
  view: function (ctrl) {
    return m('div.content.pure-u-1', {},
              m('div.form', {onsubmit: ctrl.register},
                m('form.pure-form.pure-form-aligned',
                  m('fieldset',
                    m('div.pure-control-group',
                      m('label', {for: 'username'}, 'Username'),
                      m('input#username[type="text"]', {
                                  placeholder: 'Username', pattern: '[a-zA-Z0-9_-]+',
                                  value: ctrl.user.username, required: true,
                                  onchange: function(e) {
                                    ctrl.user.username = e.currentTarget.value;
                                  }})
                    ),
                    m('div.pure-control-group',
                      m('label', {for: 'password'}, 'Password'),
                      m('input#password[type="password"]', {
                                  placeholder: 'Password', value: ctrl.user.password, required: true,
                                  onchange: function(e) {ctrl.user.password = e.currentTarget.value;}})
                    ),
                    m('div.pure-control-group',
                      m('label', {for: 'confirm'}, ''),
                      m('input#confirm[type="password"]', {
                                  placeholder: 'Password (again)', value: ctrl.user.confirm, required: true,
                                  onchange: function(e) {ctrl.user.confirm = e.currentTarget.value;}})
                    ),
                    m('div.pure-control-group',
                      m('label', {for: 'email'}, 'E-mail'),
                      m('input#email[type="email"]', {
                                  placeholder: 'E-mail address (optional)', value: ctrl.user.email,
                                  onchange: function(e) {ctrl.user.email = e.currentTarget.value;}})
                    ),
                    (ctrl.icode) ? m('div.pure-control-group',
                                    m('label', {for: 'invitecode'}, 'Invite code'),
                                    m('input#invitecode[type="text"]', {
                                                placeholder: 'Invite code', value: ctrl.user.invitecode, required: true,
                                                onchange: function(e) {ctrl.user.invitecode = e.currentTarget.value;}})): '',
                    m('div.pure-controls',
                      m('div#g-recaptcha', {'data-sitekey': document.rc_sitekey}, "Loading captcha...")
                    ),
                    m('div.pure-controls',
                      m('label.pure-checkbox', {for: 'accept_tos'},
                        m('input#accept_tos[type="checkbox"]', {required: true,
                        value: ctrl.user.accept_tos, onchange: function(e) {ctrl.user.accept_tos = e.currentTarget.checked;}}),
                        m('span', 'I accept the '),
                        m('a[href=/tos]', 'Terms of service')
                      )
                    ),
                    m('div.pure-controls',
                      m('button.pure-button.pure-button-primary[type="submit"]', 'Log in')
                    ),
                    (ctrl.success) ? m('.success', ctrl.success) : '',
                    (ctrl.err) ? m('.error', ctrl.err.map(function (lm,i) {return m('span', lm);})) : ''
                  )
                )
              )
           );
  }
};

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

user.view = function (ctrl){  // login thingy
  var u = user.udata;
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
                m('a', {class: 'glyphbutton sep', href: '#'},
                  m('i', {class: 'fa ' + function(){
                                  if (u.ntf == 0){
                                    return 'fa-envelope-o';
                                  }else{
                                    return 'fa-envelope hasmail';
                                  }
                                }(), title: 'Messages'})),
                m('a', {class: 'glyphbutton', href: '#'},
                  m('i', {class: 'fa fa-lightbulb-o', title: 'Toggle light mode'})),
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
		x.push(m('li.subinthebar', m('a', {config: m.route, href: '/s/' + ctrl.subs[i]}, ctrl.subs[i].toLowerCase())))
	}
	return x;
};

m.module(document.getElementById('th-uinfo'), {controller: user.controller, view: user.view});
m.module(document.getElementById('th-subar'), {controller: subar.controller, view: subar.view});
var lm = {};
lm.view = function () {};
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
