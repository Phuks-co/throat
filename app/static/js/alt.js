var socket = io.connect('//' + document.domain + ':' + location.port + '/alt');
console.log('foo')
function get_hostname (url) {
  if(!url){return;}
  var matches = url.match(/^https?\:\/\/([^\/?#]+)(?:[\/?#]|$)/i);
  return matches[1];
}
function renderPosts(posts){
  var l = posts.length;
  var tffs = [];
  for (var i = 0; i < l; ++i) {
    post = posts[i]
    postdomain = get_hostname(post['link'])
    console.log(postdomain)
    tffs.push(m('div.post.pure-g', {pid: post['pid']},
               m('div.pure-u-8-24.pure-u-sm-3-24.misctainer',
                m('div.votebuttons.pure-u-1-24.pure-u-sm-1-24',
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
                }(), m('span.pure-badge', m('i.fa.fa-comments'), ' ', post.comments))
               ),
                m('div.pure-u-16-24.pure-u-sm-21-24.pbody',
                  function () {
                    if (post.ptype == 0){
                      return m('a.title[href=/s/' + post['sub']['name'] + '/' + post['pid'] + ']', {}, post['title']);
                    } else {
                      return [m('a.title', {href: post['link']}, post['title']),
                              m('span.domain', ' (', m('a[href=#]', {}, postdomain), ')')
                              ];
                    }
                  }(),
                  m('div.author', 'posted ',
                    m('time-ago', {datetime: post.posted}),
                    ' by ', (post.username == '[Deleted]') ? '[Deleted]' : m('a', {href: '/u/'+ post.username, config: m.route}, post.username),
                    ' on ', m('a', {href: '/s/' + post.sub.name, config: m.route}, post.sub.name)
                  )
                )
              ));
  }
  return tffs;
}

var index = {
  controller: function (){
    var ctrl = this;
    ctrl.err = '';
    ctrl.posts = []
    ctrl.get_posts = function () {
      m.startComputation();
      m.request({
        method: 'GET',
        url: '/do/get_frontpage/all/new'
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
    }
    ctrl.get_posts();
  },
  view: function (ctrl) {
    if (ctrl.err != ''){
      return m('div.content.pure-u-1', {}, "Error loading posts: " + ctrl.err);
    }else {
      return [m('div.content.pure-u-1 pure-u-sm-18-24', {}, renderPosts(ctrl.posts)),
              m('div.sidebar.pure-u-1 pure-u-sm-6-24')];
    }
  }
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

m.route.mode = "hash";

/* routing */
m.route(document.getElementById('th-main'), "/", {
    "/": index,
    "/login": login,
    "/register": register
});

/* User view thingy controller */
var user = {};

user.vm = new function () {
  var vm = {};
  vm.init = function () {
    vm.udata = m.prop('lel');  // loadin'
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
        vm.udata(data);
        m.endComputation();
      });
    })();
  };
  return vm;
};

user.controller = function(){
  user.vm.init();
};

user.view = function (ctrl){
  var u = user.vm.udata()
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

m.module(document.getElementById('th-uinfo'), {controller: user.controller, view: user.view});

/* Menu */
(function (window, document) {
  var menu = document.getElementById('menu'),
    WINDOW_CHANGE_EVENT = ('onorientationchange' in window) ? 'orientationchange':'resize';

  function toggleHorizontal() {
    [].forEach.call(
      document.getElementById('menu').querySelectorAll('.custom-can-transform'),
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
