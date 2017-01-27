/* Index routes:
 *  - [X] all_new
 *  - [X] all_top
 *  - [X] all_hot
 *  - [X] home_hot
 *  - [X] home_top
 *  - [X] home_new
 */

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
      url: '/do/get_posts/' + type + '/' + sort
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
};
all_hot.controller = function() {return all_hot.control('all', 'hot');};
all_hot.view = function (ctrl) {
  if (ctrl.err !== ''){
    return m('div.content.pure-u-1', {}, "Error loading posts: " + ctrl.err);
  }else {
    if (!ctrl.posts.length) {

      return [m('div.content.pure-u-1 pure-u-md-18-24', {}, 'Loading...'),
              m('div.sidebar.pure-u-1 pure-u-md-6-24')];
    } else {
      return [m('div.content.pure-u-1 pure-u-md-18-24', {}, renderPosts(ctrl.posts, ctrl.sub)),
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
