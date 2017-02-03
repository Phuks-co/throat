/* sub-related views:
 *  - [X] sub_new
 *  - [X] sub_top
 *  - [X] sub_hot
 *  - [ ] sidebar
 *  - [ ] sub settings
 *  - [ ] moderators
 *  - [ ] sub log
 *  - [ ] stylesheets
 */

var current_sub = {};

var sub_auto = {
  oninit: function (vnode){
    current_sub = {};
    var ctrl = this;
    var page = m.route.param('page');
    ctrl.err = '';
    ctrl.posts = [];
    ctrl.get_posts = function () {
      window.stop();  // We're going to change pages, so cancel all requests.
      m.request({
        method: 'GET',
        url: '/api/v1/getSub/' + m.route.param('sub')
      }).then(function(res) {
        ctrl.sub = res.sub;
        current_sub = res.sub;
        if(!vnode.attrs) {
          vnode.attrs = ctrl.sub.sort;
        }
        m.request({
          method: 'GET',
          url: '/api/v1/listPosts/' + ctrl.sub.name + '/' + vnode.attrs + '/' + ((page) ? + page : '1')
        }).then(function(res) {
          if (res.status == 'ok'){
            ctrl.posts = res.posts;
          } else {
            ctrl.err = res.error;
          }
        }).catch(function(err) {
          ctrl.err = [err];
        });
      });
    };
    m.redraw();
    ctrl.get_posts();
    return ctrl;
  },
  view: function(ctrl) { return all_hot.view(ctrl); }
};

var sub_hot = {
  oninit: function () {return sub_auto.oninit('hot');},
  view: function (ctrl) { return sub_auto.view(ctrl);}
};

var sub_top = {
  oninit: function () {return sub_auto.oninit('top');},
  view: function (ctrl) { return sub_auto.view(ctrl);}
};

var sub_new = {
  oninit: function () {return sub_auto.oninit('new');},
  view: function (ctrl) { return sub_auto.view(ctrl);}
};
