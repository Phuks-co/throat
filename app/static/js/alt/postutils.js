/* Post rendering related functions */

/* The mother of all the expandos */
function postWrapper(post) {
  post.domain = get_hostname(post.link);
  post.close_expando = function () {
    m.startComputation();
    post.expando = false;
    m.endComputation();
  };

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
    var id = vineID(post.link);
    if (id) {
      m.startComputation();
      post.expando = m('div.pure-g', m('div.pure-u-1.pure-u-md-3-24'), m('div.pure-u-1.pure-u-md-13-24', m('div.iframewrapper',
                      m('iframe', {width: '100%', src: 'https://vine.co/v/' + id + '/embed/simple'})
                    )));
      m.endComputation();
    }
  };

  post.vimeo_expando = function () {
    var id = vimeoID(post.link);
    if (id) {
      m.startComputation();
      post.expando = m('div.pure-g', m('div.pure-u-1.pure-u-md-3-24'), m('div.pure-u-1.pure-u-md-13-24', m('div.iframewrapper',
                      m('iframe', {width: '100%', src: 'https://player.vimeo.com/video/' + id})
                    )));
      m.endComputation();
    }
  };

  post.streamable_expando = function () {
    var id = streamableID(post.link);
    if (id) {
      m.startComputation();
      post.expando = m('div.pure-g', m('div.pure-u-1.pure-u-md-3-24'), m('div.pure-u-1.pure-u-md-13-24', m('div.iframewrapper',
                      m('iframe', {width: '100%', src: 'https://streamable.com/e/' + id})
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
    var id = imgurID(post.link);
    if (id) {
      m.startComputation();
      post.expando = m('div.pure-g', m('div.pure-u-1.pure-u-md-3-24'), m('div.pure-u-1.pure-u-md-13-24',
                      m('video', {preload: 'auto', autoplay: 'autoplay', loop: 'loop'},
                        m('source', {src: 'https://i.imgur.com/' + id + '.mp4'})
                      )
                    ));
      m.endComputation();
    }
  };

  post.tweet_expando = function () {
    m.startComputation();
    m.request({
      dataType: 'jsonp',
      url: 'https://publish.twitter.com/oembed?url=' + post.link + '&omit_script=true'
    }).then(function(res) {
        if (res.version == '1.0') {
          post.expando = m('div.pure-g', m('div.pure-u-1.pure-u-md-3-24'), m('div.pure-u-1.pure-u-md-13-24', m('div.tweetwrapper',
                          m('span', m.trust(md.makeHtml(res.html)))
                        )));
        }
        m.endComputation();
    });
  };

  post.xkcd_expando = function () {
    var id = xkcdID(post.link);
    if (id) {
      m.startComputation();
      m.request({
        dataType: 'jsonp',
        url: 'https://dynamic.xkcd.com/api-0/jsonp/comic/' + id
      }).then(function(res) {
          if (res.num == id) {
            post.expando = m('div.pure-g', m('div.pure-u-1.pure-u-md-3-24'), m('div.pure-u-1.pure-u-md-13-24',
                            [m('div.expandotxt', res.safe_title + ': ' + res.alt), m('img', {src: res.img})]
                          ));
          }
          m.endComputation();
      });
    }
  };

  post.text_expando = function () {
    m.startComputation();
    m.request({
      method: 'GET',
      url: '/do/get_post_md/' + post.pid
    }).then(function(res) {
        if (res.status == 'ok'){
          post.expando = m('div.pure-g', m('div.pure-u-1.pure-u-md-3-24'), m('div.pure-u-1.pure-u-md-13-24 expandotxt',
                          m('span', m.trust(md.makeHtml(res.content)))
                        ));
        }
        m.endComputation();
    });
  };

  return post;
}
function decide_thumb(post) {
          if (post.thumbnail !== '' && post.ptype == 1){
            return m('img', {src: thumbs + post.thumbnail});
          }else if(post.ptype == 1){
            return m('span.placeholder', m('i.fa.fa-link.fa-inverse'));
          }else{
            return m('span.placeholder',
                     m('i.fa.fa-comments.fa-inverse')
                    );
  }
}
function work_expandos (post) {
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
      }else if (post.domain == 'streamable.com') {
        return m('div.expando', {onclick: post.streamable_expando}, m('i.fa.fa-play'));
      }
    } else { // text post
      if (post.content) {
        return m('div.expando', {onclick: post.text_expando}, m('i.fa.fa-file-text-o'));
      }
    }
  }
}

/* Returns the necessary stuff to render a list of posts */
function renderPosts(posts, sub){
  var l = posts.length;
  var tffs = [];
  for (var i = 0; i < l; ++i) {
    post = postWrapper(posts[i]);
    if (sub) {
      post.sub = sub;
    }
    tffs.push(m('div.post.pure-g', {pid: post.pid},
               m('div.pure-u-8-24.pure-u-md-4-24.misctainer',
                m('div.votebuttons.pure-u-1-24.pure-u-md-1-24',
                  m('div.fa.fa-chevron-up.upvote', {class: (post.vote == 1) ? 'upvoted' : '', title: 'Upvote'}),
                  m('div.score', post.score),
                  m('div.fa.fa-chevron-down.downvote', {class: (post.vote === 0) ? 'downvoted' : '', title: 'Downvote'})
                ), // UV/DV/score
                m('div.thcontainer', m('div.thumbnail', decide_thumb(post)),
                m('span.pure-badge', m('i.fa.fa-comments'), ' ', post.comments)) // thumbnail
               ),
                m('div.pure-u-16-24.pure-u-md-20-24.pbody',
									m('div.post-heading',
                    ((post.ptype === 0) ? m('a.title[href=/s/' + post.sub.name + '/' + post.pid + ']', {config: m.route}, post.title) : [m('a.title', {href: post.link}, post.title), m('span.domain', ' (', m('a', {href: '/domain/' + post.domain, config: m.route}, post.domain), ')')])
	                ),
                  m('div.author', work_expandos(post),'posted ',
                    m('time-ago', {datetime: post.posted}),
                    ' by ', (post.username == '[Deleted]') ? '[Deleted]' : m('a', {href: '/u/'+ post.username, config: m.route}, post.username),
                    (!sub) ? [' on ', m('a', {href: '/s/' + post.sub.name, config: m.route}, post.sub.name)] : null
                  )
                )
              ),
              (post.expando) ? post.expando : null);
  }
  return tffs;
}
