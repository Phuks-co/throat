/* Index routes:
 *  - [X] all_new
 *  - [X] all_top
 *  - [X] all_hot
 *  - [X] home_hot
 *  - [X] home_top
 *  - [X] home_new
 */


function gettop5sidebar (posts) {
  list = [];
  for (var i in posts) {
    list.push(m('li', m('span.TPScore', posts[i].score), m('a', {href: '/s/' + posts[i].sub.name + '/' + posts[i].pid, oncreate: m.route.link}, posts[i].title),
                      m('span.stuff', 'posted ', m('time-ago', {datetime: posts[i].posted}), ' in ', m('a', {href: '/s/' + posts[i].sub.name , oncreate: m.route.link}, posts[i].sub.name)  )));
  }
  return list;
}


function getsidebar (ctrl) {
  if (ctrl.sub) {
    return [m('h4', ctrl.sub.name), m('div.sidebarrow', ctrl.sub.subscribercount + ' subscribers'), m('div.sidebarrow', 'Mod: ' + ctrl.sub.owner)];
  } else {
    list = [];
    return [m('div.sidebarrow',
              m('div.top5title', 'Top posts in the last 24 hours',
                m('ul.top5', gettop5sidebar(ctrl.topposts)
            )))];
  }
}


var all_hot = {}; // all_hot is the base for all the other sorters!
all_hot.control = function (type, sort){
  var ctrl = this;
  var page = m.route.param('page');
  ctrl.err = '';
  ctrl.posts = null;
  ctrl.topposts = [];
  ctrl.get_posts = function () {
    window.stop();  // We're going to change pages, so cancel all requests.
    m.request({
      method: 'GET',
      url: '/api/v1/listPosts/' + type + '/' + sort + '/' + ((page) ? page : '1')
    }).then(function(res) {
      if (res.status == 'ok'){
        ctrl.posts = res.posts;
      } else {
        ctrl.err = res.error;
      }
    }).catch(function(err) {
      ctrl.err = [err];
    });
    if (!ctrl.sub) {
      m.request({
        method: 'GET',
        url: '/api/v1/getTopPosts/day'
      }).then(function(res2) {
        if (res2.status == 'ok'){
          ctrl.topposts = res2.posts;
        } else {
          ctrl.err = res2.error;
        }
      });
    }
  };
  m.redraw();
  ctrl.get_posts();
  return ctrl;
};
all_hot.oninit = function() {return all_hot.control('all', 'hot');};
all_hot.view = function () {
  var ctrl = this;
  if (ctrl.err !== ''){
    return m('div.content.pure-u-1', {}, "Error loading posts: " + ctrl.err);
  }else {
    if (ctrl.posts === null) {
      return [m('div.content.pure-u-1 pure-u-md-18-24', {}, 'Loading...'),
              m('div.sidebar.pure-u-1 pure-u-md-6-24')];
    } else if (ctrl.posts.length === 0){
      return [m('div.content.pure-u-1 pure-u-md-18-24', {}, 'No posts here'),
              m('div.sidebar.pure-u-1 pure-u-md-6-24')];
    } else {
      var page = m.route.param('page');
      if (!page) {
        page = '1';
        nroute = m.route.get() + '/2';
      } else {
        r = m.route.get();
        var nopage = r.slice(0, r.lastIndexOf("/"));
        nroute = nopage + '/' + ((page*1)+1);
        proute = nopage + '/' + ((page*1)-1);
        if (page == '2') {proute=nopage;}
      }
      return [m('div.content.pure-u-1 pure-u-md-18-24', {}, renderPosts(ctrl.posts, ctrl.sub),
              m('div.pagenav.pure-u-1 pure-u-md-18-24',
              ((page == 1) ?
                [m('a.next', {href: nroute, oncreate: m.route.link}, 'next')] :
                [m('a.prev', {href: proute, oncreate: m.route.link}, 'prev'),
                m('a.next', {href: nroute, oncreate: m.route.link}, 'next')])
              )),
              m('div.sidebar.pure-u-1 pure-u-md-6-24',
                m('div.sidebarcontent', getsidebar (ctrl))
              )];
    }
  }
};

var all_new = {
  oninit: function (){ return all_hot.control('all', 'new'); },
  view: function(ctrl) { return all_hot.view(ctrl); }
};

var all_top = {
  oninit: function (){ return all_hot.control('all', 'top'); },
  view: function(ctrl) { return all_hot.view(ctrl); }
};

var home_hot = {
  oninit: function (){ return all_hot.control('home', 'hot'); },
  view: function(ctrl) { return all_hot.view(ctrl); }
};

var home_new = {
  oninit: function (){ return all_hot.control('home', 'new'); },
  view: function(ctrl) { return all_hot.view(ctrl); }
};


var home_top = {
  oninit: function (){ return all_hot.control('home', 'top'); },
  view: function(ctrl) { return all_hot.view(ctrl); }
};
