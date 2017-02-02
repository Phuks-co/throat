/* Post-related views:
 *  - [ ] View post
 *     - [ ] View comments
 *     - [ ] Edit comments
 *     - [ ] Delete comments
 *  - [ ] Create post
 *  - [ ] Edit post
 *  - [ ] Delete post
 */

 function getpostsidebar (ctrl) {
     return [m('div.sidebarrow', 'Score: ' + ctrl.post.score),
              m('h4', ctrl.sub.name),
              m('div.sidebarrow', ctrl.sub.subscribercount + ' subscribers'),
              m('div.sidebarrow', 'Mod: ' + ctrl.sub.owner)
            ];
 }

 var view_post = {
   controller: function (){
     var ctrl = this;
     ctrl.err = '';
     ctrl.sub = m.route.param('sub');
     m.startComputation();
     window.stop();  // We're going to change pages, so cancel all requests.
     m.request({
       method: 'GET',
       url: '/api/v1/getPost/' + m.route.param('pid')
     }).then(function(res) {
         if (res.status == 'ok'){
           ctrl.post = res.post;
           m.request({
             method: 'GET',
             url: '/api/v1/getSub/' + ctrl.post.sub
           }).then(function(res) {
             ctrl.sub = res.sub;
             current_sub = res.sub;
           });
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
       return m('div.content.pure-u-1', {}, "Error loading post: " + ctrl.err);
     }else {
       if (!ctrl.post) {
         return [m('div.content.pure-u-1 pure-u-md-18-24', {}, 'Loading...'),
                 m('div.sidebar.pure-u-1 pure-u-md-6-24')];
       } else {
         var post = ctrl.post;
         return [m('div.content.pure-u-1 pure-u-md-18-24', {},
                  m('article.post.center',
                    m('div.head',
                      (post.nsfw) ? m('div.bgred', {title: 'Not safe for work'}, 'NSFW') : '',
                      (post.thumbnail) ? m('div.thpostcontainer', m('div.thumbnail', decide_thumb(post))) : '',
                      ((post.ptype === 0) ? m('div.title', post.title) :
                        [m('a.title', {href: post.link}, post.title),
                          m('span.domain', ' (', m('a', {href: '/domain/' + get_hostname(post.link), config: m.route}, get_hostname(post.link)), ')')]),
                      m('div.postInfo', (post.ptype === 1) ? work_expandos(post) : '','posted ',
                        m('time-ago', {datetime: post.posted}),
                        function () {
                          switch (post.deleted){
                            case 0:
                              return  m('span',' by ', m('a', {href: '/u/' + post.user, config: m.route}, post.user));
                            case 1:
                              return ' by [Deleted by user]';
                            case 2:
                              return ' by [Deleted]';
                          }
                        }()
                        /* TODO: Save, edit, delete and flair buttons */
                      ),
                      [(post.ptype === 0) ? m('div.postContent', m.trust(md.makeHtml(post.content))) : '',
                      (post.expando) ? post.expando : null]
                    )
                  )
                ),
                  m('div.sidebar.pure-u-1 pure-u-md-6-24',
                    m('div.sidebarcontent', getpostsidebar (ctrl))
                  )];
       }
     }
   }
 };
