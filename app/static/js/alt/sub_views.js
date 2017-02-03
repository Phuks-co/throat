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
  oninit: function (sort){
    current_sub = {};
    var ctrl = this;
    var page = m.route.param('page');
    ctrl.err = '';
    ctrl.posts = null;
    ctrl.get_posts = function () {
      window.stop();  // We're going to change pages, so cancel all requests.
      m.request({
        method: 'GET',
        url: '/api/v1/getSub/' + m.route.param('sub'),
        background:true
      }).then(function(res) {
        ctrl.sub = res.sub;
        current_sub = res.sub;
        if(!sort) {
          sort = ctrl.sub.sort;
        }
        m.request({
          method: 'GET',
          url: '/api/v1/listPosts/' + ctrl.sub.name + '/' + sort + '/' + ((page) ? + page : '1')
        }).then(function(res) {
          if (res.status == 'ok'){
            ctrl.posts = res.posts;
          } else {
            ctrl.err = res.error;
          }
          m.redraw();
        }).catch(function(err) {
          ctrl.err = [err];
        });
      });
    };
    ctrl.get_posts();
    return ctrl;
  },
  view: function(ctrl) { return renderPostList(ctrl.state); }
};

var sub_hot = {
  oninit: function (ctrl) {ctrl.state = sub_auto.oninit('hot');},
  view: function (ctrl) { return sub_auto.view(ctrl);}
};

var sub_top = {
  oninit: function (ctrl) {ctrl.state = sub_auto.oninit('top');},
  view: function (ctrl) {return sub_auto.view(ctrl);}
};

var sub_new = {
  oninit: function (ctrl) {ctrl.state = sub_auto.oninit('new');},
  view: function (ctrl) { return sub_auto.view(ctrl);}
};
