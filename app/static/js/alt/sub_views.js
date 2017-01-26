/* sub-related views:
 *  - [ ] sub_new
 *  - [ ] sub_top
 *  - [ ] sub_hot
 *  - [ ] sidebar
 *  - [ ] sub settings
 *  - [ ] moderators
 *  - [ ] sub log
 *  - [ ] stylesheets
 */

var sub_auto = {
  controller: function (){
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
        ctrl.sub = res.sub
        m.request({
          method: 'GET',
          url: '/do/get_posts/' + ctrl.sub.name + '/' + ctrl.sub.sort
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
