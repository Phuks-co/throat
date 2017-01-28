/* User views:
 *   - [X] login
 *   - [X] register
 *   - [ ] profile
 *   - [ ] settings
 *   - [ ] posts
 *   - [ ] comments
 */


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


var view_user = {
  controller: function (){
    var ctrl = this;
    ctrl.err = '';
    ctrl.user = m.route.param('user');
    m.startComputation();
    window.stop();  // We're going to change pages, so cancel all requests.
    m.request({
      method: 'GET',
      url: '/do/get_user/' + m.route.param('user')
    }).then(function(res) {
        if (res.status == 'ok'){
          ctrl.user = res.user;
        } else {
          ctrl.err = res.error;
        }
        m.endComputation();
    }).catch(function(err) {
      ctrl.err = [err];
      m.endComputation();
    });
  },
  view: function(ctrl) {
    if (ctrl.err !== ''){
      return m('div.content.pure-u-1', {}, "Error loading user: " + ctrl.err);
    }else {
      if (!ctrl.user) {
        return [m('div.content.pure-u-1 pure-u-md-18-24', {}, 'Loading...'),
                m('div.sidebar.pure-u-1 pure-u-md-6-24')];
      } else if (ctrl.status == 10) {
        return [m('div.content.pure-u-1 pure-u-md-18-24', {}, '[Deleted]'),
                m('div.sidebar.pure-u-1 pure-u-md-6-24')];

      } else {
        var user = ctrl.user;
        return [m('div.content.pure-u-1 pure-u-md-18-24', {},
                 [m('div.user.center', user.name),
                  m('div.user.center', 'Joined: ' + user.joindate),
                  m('div.user.center', user.score + 'xp')]

               ),
                m('div.sidebar.pure-u-1 pure-u-md-6-24')];
      }
    }
  }
};


var view_user_posts = {
  controller: function (sort){
    var ctrl = this;
    var page = m.route.param('page')
    if(!page) {
      page = '1';
    }
    ctrl.err = '';
    ctrl.posts = [];
    ctrl.get_posts = function () {
      m.startComputation();
      window.stop();  // We're going to change pages, so cancel all requests.
        m.request({
          method: 'GET',
          url: '/do/get_userposts/' + m.route.param('user') + ((page) ? '/' + page : '')
        }).then(function(res) {
            if (res.status == 'ok'){
              ctrl.posts = res.posts;
            } else {
              ctrl.err = res.error;
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
  },
  view: function(ctrl) { return all_hot.view(ctrl); }
};
