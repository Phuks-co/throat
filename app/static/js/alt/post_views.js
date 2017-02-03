/* Post-related views:
 *  - [X] View post
 *    - [ ] Edit post
 *    - [ ] Delete post
 *    - [ ] Flair post
 *  - [ ] View comments
 *    - [ ] Edit comments
 *    - [ ] Delete comments
 *  - [ ] Create post
 */

 function getpostsidebar (ctrl) {
     return [m('div.sidebarrow', 'Score: ' + ctrl.post.score),
              m('h4', ctrl.sub.name),
              m('div.sidebarrow', ctrl.sub.subscribercount + ' subscribers'),
              m('div.sidebarrow', 'Mod: ' + ctrl.sub.owner)
            ];
 }
function render_comments(comments, d) {
  var r = [];
   if(!d){d=0;}
   for (var i in comments) {
     comm = comments[i];
     r.push(m('article.comment', {class: (d % 2 == 1) ? 'even' : 'odd'},
             m('div.commentHead', // comment head, all comment info and collapse button
               m('span', (comm.collapsed) ? '[-]' : '[+]'), ' ', // toggle
               m('a.author', {href: '/u/' + comm.user, oncreate: m.route.link}, comm.user), ' ',
               m('time-ago', {datetime: comm.posted}),
               (comm.lastedit) ? [' (edited ', m('time-ago', {datetime: comm.lastedit}), ')'] : ''
             ),
             m('div.commentContent', comm.content),
             render_comments(comm.children, (d+1), (d+r.length))
           ));
   }
   return r;
 }

 var view_post = {
   oninit: function (){
     var ctrl = this;
     ctrl.err = '';
     ctrl.sub = m.route.param('sub');
     window.stop();  // We're going to change pages, so cancel all requests.
     m.request({
       method: 'GET',
       url: '/api/v1/getPost/' + m.route.param('pid')
     }).then(function(res) {
       if (res.status == 'ok'){
         ctrl.post = res.post;
       } else {
         ctrl.err = res.error;
       }
     }).catch(function(err) {
       ctrl.err = [err];
     });
     m.request({
       method: 'GET',
       url: '/api/v1/getSub/' + ctrl.sub
     }).then(function(res) {
       ctrl.sub = res.sub;
       current_sub = res.sub;
     });

     m.request({
       method: 'GET',
       url: '/api/v1/getComments/' + m.route.param('pid') + '/0/0'
     }).then(function(res) {
       ctrl.comments = res.comments;
     });
   },
   view: function(ctrl) {
     ctrl = this;
     if (ctrl.err !== ''){
       return m('div.content.pure-u-1', {}, "Error loading post: " + ctrl.err);
     }else {
       if (!ctrl.post) {
         return [m('div.content.pure-u-1 pure-u-md-18-24', {}, 'Loading...'),
                 m('div.sidebar.pure-u-1 pure-u-md-6-24')];
       } else {
         var post = postWrapper(ctrl.post);
         return [m('div.content.pure-u-1 pure-u-md-18-24', {},
                  m('article.post.center',
                    m('div.head',
                      (post.nsfw) ? m('div.bgred', {title: 'Not safe for work'}, 'NSFW') : '',
                      m('div.thpostcontainer', m('div.thumbnail', decide_thumb(post))),
                      ((post.ptype === 0) ? m('a.title', {href: '/s/' + post.sub + '/' + post.pid, oncreate: m.route.link} , post.title) :
                        [m('a.title', {href: post.link}, post.title),
                          m('span.domain', ' (', m('a', {href: '/domain/' + get_hostname(post.link), oncreate: m.route.link}, get_hostname(post.link)), ')')]),
                      m('div.postInfo', (post.ptype === 1) ? work_expandos(post) : '','posted ',
                        m('time-ago', {datetime: post.posted}),
                        function () {
                          switch (post.deleted){
                            case 0:
                              return  m('span',' by ', m('a', {href: '/u/' + post.user, oncreate: m.route.link}, post.user));
                            case 1:
                              return ' by [Deleted by user]';
                            case 2:
                              return ' by [Deleted]';
                          }
                        }()
                        /* TODO: Save, edit, delete and flair buttons */
                      )
                    ),
                    [(post.ptype === 0) ? m('div.postContent', m.trust(md.makeHtml(post.content))) : '']
                  ),
                  m('div.comments',
                    function () {
                      if(ctrl.comments === undefined) {
                        return m('span', 'Loading comments...');
                      }else if(ctrl.comments.length === 0){
                        return m('h3', 'No comments here... yet.');
                      }else{
                        return render_comments(ctrl.comments);
                      }
                    }()
                  ) // comments
                ),
                m('div.sidebar.pure-u-1 pure-u-md-6-24',
                  m('div.sidebarcontent', getpostsidebar (ctrl))
                )];
       }
     }
   }
 };
