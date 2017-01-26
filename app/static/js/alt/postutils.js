/* Post rendering related functions */

/* The mother of all the expandos */
function postWrapper(post) {
  var post = post;
  post.domain = get_hostname(post.link);
  post.close_expando = function () {
    m.startComputation();
    post.expando = false;
    m.endComputation();
  }

  post.youtube_expando = function () {
    var id = youtubeID(post.link);
    if (id) {
      m.startComputation();
      post.expando = m('div.pure-g', m('div.pure-u-1.pure-u-md-3-24'), m('div.pure-u-1.pure-u-md-13-24', m('div.iframewrapper',
                      m('iframe', {width: '100%', src: 'https://www.youtube.com/embed/' + id})
                    )));
      m.endComputation();
    }
  };

  post.gfycat_expando = function () {
    var id = gfycatID(post.link);
    if (id) {
      m.startComputation();
      post.expando = m('div.pure-g', m('div.pure-u-1.pure-u-md-3-24'), m('div.pure-u-1.pure-u-md-13-24', m('div.iframewrapper',
                      m('iframe', {width: '100%', src: 'https://gfycat.com/ifr/' + id})
                    )));
      m.endComputation();
    }
  };

  post.vine_expando = function () {
    var id = vineID(post.link)
    if (id) {
      m.startComputation();
      post.expando = m('div.pure-g', m('div.pure-u-1.pure-u-md-3-24'), m('div.pure-u-1.pure-u-md-13-24', m('div.iframewrapper',
                      m('iframe', {width: '100%', src: 'https://vine.co/v/' + id + '/embed/simple'})
                    )));
      m.endComputation();
    }
  };

  post.vimeo_expando = function () {
    var id = vimeoID(post.link)
    if (id) {
      m.startComputation();
      post.expando = m('div.pure-g', m('div.pure-u-1.pure-u-md-3-24'), m('div.pure-u-1.pure-u-md-13-24', m('div.iframewrapper',
                      m('iframe', {width: '100%', src: 'https://player.vimeo.com/video/' + id})
                    )));
      m.endComputation();
    }
  };

  post.image_expando = function () {
    m.startComputation();
    post.expando = m('div.pure-g', m('div.pure-u-1.pure-u-md-3-24'), m('div.pure-u-1.pure-u-md-13-24',
                    m('img', {src: post.link, onclick: post.close_expando})
                  ));
    m.endComputation();
  };

  post.video_expando = function () {
    m.startComputation();
    post.expando = m('div.pure-g', m('div.pure-u-1.pure-u-md-3-24'), m('div.pure-u-1.pure-u-md-13-24',
                    m('video', {preload: 'auto', autoplay: 'autoplay', loop: 'loop', controls: true},
                      m('source', {src: post.link})
                    )
                  ));
    m.endComputation();
  };

  post.imgur_gifv_expando = function () {
    m.startComputation();
    post.expando = m('div.pure-g', m('div.pure-u-1.pure-u-md-3-24'), m('div.pure-u-1.pure-u-md-13-24',
                    m('video', {preload: 'auto', autoplay: 'autoplay', loop: 'loop'},
                      m('source', {src: 'https://i.imgur.com/' + imgurID(post.link) + '.mp4'})
                    )
                  ));
    m.endComputation();
  };

  post.tweet_expando = function () {
    m.startComputation();
    post.expando = m('div.pure-g', m('div.pure-u-1.pure-u-md-3-24'), m('div.pure-u-1.pure-u-md-13-24', m('div.iframewrapper',
                    m('iframe', {width: '100%', src: 'https://twitframe.com/show?url=' + post.link})
                  )));
    m.endComputation();
  };

  post.xkcd_expando = function () {
    m.startComputation();
    m.request({
      dataType: "jsonp",
      url: 'https://dynamic.xkcd.com/api-0/jsonp/comic/' + id
    }).then(function(res) {
        if (res.num == xkcdID(post.link)) {
          post.expando = m('div.pure-g', m('div.pure-u-1.pure-u-md-3-24'), m('div.pure-u-1.pure-u-md-13-24',
                          m('img', {src: res.img})
                        ));
        }
        m.endComputation();
    });
  };

  post.text_expando = function () {
    m.startComputation();
    m.request({
      method: 'GET',
      url: '/do/get_post_md/' + post.pid
    }).then(function(res) {
        if (res.status == 'ok'){
          post.expando = m('div.pure-g', m('div.pure-u-1.pure-u-md-3-24'), m('div.pure-u-1.pure-u-md-13-24',
                          m('span', m.trust(md.makeHtml(res.content)))
                        ));
        }
        m.endComputation();
    });
  };

  return post;
}


/* Returns the necessary stuff to render a list of posts */
function renderPosts(posts){
  var l = posts.length;
  var tffs = [];
  for (var i = 0; i < l; ++i) {
    post = postWrapper(posts[i])
    tffs.push(m('div.post.pure-g', {pid: post['pid']},
               m('div.pure-u-8-24.pure-u-md-4-24.misctainer',
                m('div.votebuttons.pure-u-1-24.pure-u-md-1-24',
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
                }(), m('span.pure-badge', m('i.fa.fa-comments'), ' ', post.comments)) // thumbnail
               ),
                m('div.pure-u-16-24.pure-u-md-20-24.pbody',
									m('div.post-heading',
	                  function () {
	                    if (post.ptype == 0){
	                      return m('a.title[href=/s/' + post['sub']['name'] + '/' + post['pid'] + ']', {}, post['title']);
	                    } else {
	                      return [m('a.title', {href: post['link']}, post['title']),
	                              m('span.domain', ' (', m('a[href=#]', {}, post.domain), ')')
	                              ];
	                    }
	                  }()),
                  m('div.author',
                    function () {
                      if(post.expando){
                        return m('div.expando', {onclick: post.close_expando}, m('i.fa.fa-close'));
                      }else{
                        if (post.ptype == 1){
                          if ((post.domain == 'youtube.com') || (post.domain == 'www.youtube.com') || (post.domain == 'youtu.be')) {
                            return m('div.expando', {onclick: post.youtube_expando}, m('i.fa.fa-youtube-play'));
                          }else if (post.domain == 'gfycat.com') {
                            return m('div.expando', {onclick: post.gfycat_expando}, m('i.fa.fa-play'));
                          }else if (post.domain == 'vine.co') {
                            return m('div.expando', {onclick: post.vine_expando}, m('i.fa.fa-vine'));
                          }else if (post.domain == 'vimeo.com') {
                            return m('div.expando', {onclick: post.vimeo_expando}, m('i.fa.fa-vimeo'));
                          }else if(/\.(png|jpg|gif|tiff|svg|bmp|jpeg)$/i.test(post.link)) {
                            return m('div.expando', {onclick: post.image_expando}, m('i.fa.fa-image'));
                          }else if (/\.(mp4|webm)$/i.test(post.link)) {
                            return m('div.expando', {onclick: post.video_expando}, m('i.fa.fa-play'));
                          }else if (post.domain == 'i.imgur.com' && /\.gifv$/i.test(post.link)) {
                            return m('div.expando', {onclick: post.imgur_gifv_expando}, m('i.fa.fa-play'));
                          }else if (post.domain == 'twitter.com') {
                            return m('div.expando', {onclick: post.tweet_expando}, m('i.fa.fa-twitter'));
                          }else if (post.domain == 'xkcd.com') {
                            return m('div.expando', {onclick: post.xkcd_expando}, m('i.fa.fa-image'));
                          }
                        } else { // text post
                          if (post.content) {
                            return m('div.expando', {onclick: post.text_expando}, m('i.fa.fa-file-text-o'));
                          }
                        }
                      }
                    }(),'posted ',
                    m('time-ago', {datetime: post.posted}),
                    ' by ', (post.username == '[Deleted]') ? '[Deleted]' : m('a', {href: '/u/'+ post.username, config: m.route}, post.username),
                    ' on ', m('a', {href: '/s/' + post.sub.name, config: m.route}, post.sub.name)
                  )
                )
              ),
              function () {
                if(post.expando){
                  return post.expando;
                }
              }());
  }
  return tffs;
}
