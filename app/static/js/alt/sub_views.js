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
  controller: function (sort){
    current_sub = {};
    var ctrl = this;
    ctrl.err = '';
    ctrl.posts = [];
    ctrl.get_posts = function () {
      m.startComputation();
      window.stop();  // We're going to change pages, so cancel all requests.
      m.request({
        method: 'GET',
        url: '/do/get_sub/' + m.route.param('sub')
      }).then(function(res) {
        ctrl.sub = res.sub;
        current_sub = res.sub;
        if(!sort) {
          sort = ctrl.sub.sort;
        }
        m.request({
          method: 'GET',
          url: '/do/get_posts/' + ctrl.sub.name + '/' + sort
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
      })
    };
    m.redraw();
    ctrl.get_posts();
    return ctrl;
  },
  view: function(ctrl) { return all_hot.view(ctrl); }
}

var sub_hot = {
  controller: function () {return sub_auto.controller('hot');},
  view: function (ctrl) { return sub_auto.view(ctrl);}
};

var sub_top = {
  controller: function () {return sub_auto.controller('top');},
  view: function (ctrl) { return sub_auto.view(ctrl);}
};

var sub_new = {
  controller: function () {return sub_auto.controller('new');},
  view: function (ctrl) { return sub_auto.view(ctrl);}
};
