// Post page-related code.
import TextConfirm from  './utils/TextConfirm';
import $ from 'jquery';
import Icons from './Icon';
import u from './Util';
import initializeEditor from './Editor';

// Saving/unsaving posts.
u.sub('.savepost', 'click', function(e){
  var tg = e.currentTarget;
  u.post('/do/save_post/' + tg.getAttribute('data-pid'), {}, function(data){tg.innerHTML = 'saved';});
});

u.sub('.removesavedpost', 'click', function(e){
  var tg = e.currentTarget;
  u.post('/do/remove_saved_post/' + tg.getAttribute('data-pid'), {}, function(data){tg.innerHTML = 'removed';});
})

u.sub('.delete-post', 'click', function(e){
  var tg = e.currentTarget;
  TextConfirm(this, function(){
    u.rawpost('/do/delete_post', new FormData(document.getElementById('delete-post-form')),
    function(data){
      if (data.status != "ok") {
        tg.innerHTML = 'Error.';
      } else {
        tg.innerHTML = 'removed';
        document.location.reload();
      }
    })
  });
});


// Stick post
u.sub('.stick-post', 'click', function(e){
  var pid = this.parentNode.parentNode.getAttribute('data-pid'), tg=e.currentTarget;
  TextConfirm(this, function(){
    u.rawpost('/do/stick/'+pid, new FormData(document.getElementById('delete-post-form')),
    function(data){
      if (data.status != "ok") {
        tg.innerHTML = 'Error.';
      } else {
        tg.innerHTML = 'Done';
        document.location.reload();
      }
    })
  });
});

u.sub('.announce-post', 'click', function(e){
  var pid = this.parentNode.parentNode.getAttribute('data-pid'), tg=e.currentTarget;
  TextConfirm(this, function(){
    u.post('/do/makeannouncement', {post: pid},
    function(data){
      if (data.status != "ok") {
        tg.innerHTML = 'Error.';
      } else {
        tg.innerHTML = 'Done';
        document.location.reload();
      }
    })
  });
});


u.sub('.editflair', 'click', function(e){
  document.getElementById('postflairs').style.display = 'block';
});

u.sub('.selflair', 'click', function(e){
  var pid=this.getAttribute('data-pid');
  var flair=this.getAttribute('data-flair');
  var nsub=this.getAttribute('data-sub'), tg=this;
  u.rawpost('/do/flair/' + nsub + '/' + pid + '/' + flair, new FormData(document.getElementById('delete-post-form')),
    function(data) {
      if (data.status != "ok") {
        tg.parentNode.innerHTML = 'Error. ' + data.error;
      } else {
        tg.parentNode.innerHTML = 'Done!';
        document.location.reload();
      }
    }
  )
});

u.sub('.nsfw-post', 'click', function(e){
  var pid = this.parentNode.parentNode.getAttribute('data-pid'), tg=e.currentTarget;
  TextConfirm(this, function(){
    u.rawpost('/do/nsfw', new FormData(document.getElementById('delete-post-form')),
    function(data){
      if (data.status != "ok") {
        tg.innerHTML = 'Error.';
      } else {
        tg.innerHTML = 'Done';
        document.location.reload();
      }
    })
  });
});


// post source
u.addEventForChild(document, 'click', '.post-source', function(e, qelem){
  var elem = document.getElementById('postcontent');
  var oc = elem.innerHTML;
  var back =  document.createElement( "a" );
  back.innerHTML = "<s>source</s>";
  back.onclick = function(){
    elem.innerHTML = oc;
    this.parentNode.innerHTML = '<a class="post-source">source</a>';
  };
  var h = elem.clientHeight-6;
  elem.innerHTML = '<textarea style="height: ' + h + 'px">' + document.getElementById('post-source').innerHTML + '</textarea>';
  qelem.replaceWith(back);
});


// edit post
u.addEventForChild(document, 'click', '.edit-post', function(e, qelem){
  var elem = document.getElementById('postcontent');
  var oc = elem.innerHTML;
  var back =  document.createElement( "a" );
  back.innerHTML = "<s>edit</s>";
  back.onclick = function(){
    elem.innerHTML = oc;
    this.parentNode.innerHTML = '<a class="edit-post">edit</a>';
  };
  var h = elem.clientHeight-6;
  elem.innerHTML = '<div id="editpost" class="cwrap markdown-editor"><textarea style="height: ' + h + 'px">' + document.getElementById('post-source').innerHTML + '</textarea></div><div style="display:none" class="error"></div><button class="pure-button pure-button-primary button-xsmall btn-editpost" data-pid="' + qelem.getAttribute('data-pid') +'">Save changes</button> <button class="pure-button button-xsmall btn-preview" data-pvid="editpost" >Preview</button><div class="cmpreview canclose" style="display:none;"><h4>Comment preview</h4><span class="closemsg">&times;</span><div class="cpreview-content"></div></div>';
  qelem.replaceWith(back);
  initializeEditor(document.getElementById('editpost'));
});


// comment source
u.addEventForChild(document, 'click', '.comment-source', function(e, qelem){
  var cid = qelem.getAttribute('data-cid');
  var elem = document.getElementById('content-' + cid);
  var oc = elem.innerHTML;
  var back =  document.createElement( "s" );
  back.innerHTML = "source";
  back.onclick = function(){
    elem.innerHTML = oc;
    this.parentNode.innerHTML = 'source';
  };
  var h = elem.clientHeight + 28;
  elem.innerHTML = '<div class="cwrap"><textarea style="height: ' + h + 'px">' + document.getElementById('sauce-' + cid).innerHTML + '</textarea></div>';
  var cNode = qelem.cloneNode(false);
  cNode.appendChild(back)
  qelem.parentNode.replaceChild(cNode,qelem );
});

// edit comment
u.addEventForChild(document, 'click', '.edit-comment', function(e, qelem){
  var cid = qelem.getAttribute('data-cid');
  var elem = document.getElementById('content-' + cid);
  var oc = elem.innerHTML;
  var back =  document.createElement( "s" );
  back.innerHTML = "edit";
  back.onclick = function(){
    elem.innerHTML = oc;
    this.parentNode.innerHTML = 'edit';
  };
  var h = elem.clientHeight + 28;
  elem.innerHTML = '<div class="cwrap markdown-editor" id="ecomm-'+cid+'"><textarea style="height: ' + h + 'px">' + document.getElementById('sauce-' + cid).innerHTML + '</textarea></div><div style="display:none" class="error"></div><button class="pure-button pure-button-primary button-xsmall btn-editcomment" data-cid="'+cid+'">Save changes</button> <button class="pure-button button-xsmall btn-preview" data-pvid="ecomm-'+cid+'">Preview</button><div class="cmpreview canclose" style="display:none;"><h4>Comment preview</h4><span class="closemsg">&times;</span><div class="cpreview-content"></div></div>';

  var cNode = qelem.cloneNode(false);
  cNode.appendChild(back)
  qelem.parentNode.replaceChild(cNode,qelem );
  initializeEditor(document.getElementById('ecomm-'+cid));
});

u.addEventForChild(document, 'click', '.btn-editpost', function(e, qelem){
  var content=document.querySelector('#editpost textarea').value;
  qelem.setAttribute('disabled', true);
  u.post('/do/edit_txtpost/' + qelem.getAttribute('data-pid'), {content:content},
  function(data){
    if (data.status != "ok") {
      qelem.parentNode.querySelector('.error').style.display = 'block';
      qelem.parentNode.querySelector('.error').innerHTML = 'There was an error while editing: ' + data.error;
      qelem.removeAttribute('disabled');
    } else {
      qelem.innerHTML = 'Saved.';
      document.location.reload();
    }
  }, function(){
    qelem.parentNode.querySelector('.error').style.display = 'block';
    qelem.parentNode.querySelector('.error').innerHTML = 'Could not contact the server';
    qelem.removeAttribute('disabled');
  })
});

u.addEventForChild(document, 'click', '.btn-editcomment', function(e, qelem){
  var cid = qelem.getAttribute('data-cid');
  var content = document.querySelector('#ecomm-' + cid + ' textarea').value;
  qelem.setAttribute('disabled', true);
  u.post('/do/edit_comment', {cid: cid, text: content},
  function(data){
    if (data.status != "ok") {
      qelem.parentNode.querySelector('.error').style.display = 'block';
      qelem.parentNode.querySelector('.error').innerHTML = 'There was an error while editing: ' + data.error;
      qelem.removeAttribute('disabled');
    } else {
      qelem.innerHTML = 'Saved.';
      document.location.reload();
    }
  }, function(){
    qelem.parentNode.querySelector('.error').style.display = 'block';
    qelem.parentNode.querySelector('.error').innerHTML = 'Could not contact the server';
    qelem.removeAttribute('disabled');
  })
});

u.addEventForChild(document, 'click', '.btn-preview', function(e, qelem){
  e.preventDefault();
  var content = document.querySelector('#' + qelem.getAttribute('data-pvid') + ' textarea').value;
  qelem.setAttribute('disabled', true);
  qelem.innerHTML = 'Loading...';
  u.post('/do/preview', {text: content},
  function(data){
    if (data.status == "ok") {
      qelem.parentNode.querySelector('.cpreview-content').innerHTML = data.text;
      qelem.parentNode.querySelector('.cmpreview').style.display = 'block';
    } else {
      qelem.parentNode.querySelector('.error').style.display = 'block';
      qelem.parentNode.querySelector('.error').innerHTML = 'Could not contact server ';
      qelem.removeAttribute('disabled');
    }
    qelem.removeAttribute('disabled');
    qelem.innerHTML = 'Preview';
  }, function(){
    qelem.parentNode.querySelector('.error').style.display = 'block';
    qelem.parentNode.querySelector('.error').innerHTML = 'Could not contact the server';
    qelem.removeAttribute('disabled');
  })
});

// Delete comment
u.addEventForChild(document, 'click', '.delete-comment', function(e, qelem){
  // confirmation
  var cid = qelem.getAttribute('data-cid'), tg=qelem;
  TextConfirm(this, function(){
    u.rawpost('/do/delete_comment', {cid: cid},
    function(data){
      if (data.status != "ok") {
        tg.parentNode.innerHTML = 'Error.';
      } else {
        tg.parentNode.innerHTML = 'comment removed';
        document.location.reload();
      }
    })
  });
});

// Grab post title from url
u.sub('#graburl', 'click', function(e){
  e.preventDefault();
  var uri = document.getElementById('link').value
  if(uri === ''){return;}
  this.setAttribute('disabled', true);
  this.innerHTML = 'Grabbing...';
  u.post('/do/grabtitle', {u: uri},
  function(data){
    if(data.status == 'error'){
      document.getElementById('title').value = 'Error fetching title';
      document.getElementById('graburl').removeAttribute('disabled');
      document.getElementById('graburl').innerHTML = 'Grab title';
    }else{
      document.getElementById('title').value = data.title;
      document.getElementById('graburl').removeAttribute('disabled');
      document.getElementById('graburl').innerHTML = 'Done';
    }
  })
})

// Load children
u.addEventForChild(document, 'click', '.loadchildren', function(e, qelem){
  e.preventDefault();
  u.post('/do/get_children/' + qelem.getAttribute('data-pid') + '/' + qelem.getAttribute('data-cid'), {},
  function(data){
    qelem.parentNode.innerHTML = data;
    Icons.rendericons();
  })
});

u.addEventForChild(document, 'click', '.loadsibling', function(e, qelem){
  e.preventDefault();
  var page = (qelem.getAttribute('data-page') !== '') ? qelem.getAttribute('data-page') : 1;
  var parent = (qelem.getAttribute('data-cid') !== '') ? qelem.getAttribute('data-cid') : 1;
  u.post('/do/get_sibling/' + qelem.getAttribute('data-pid') + '/' + parent + '/' + page, {},
  function(data){
    qelem.outerHTML = data;
    Icons.rendericons();
  })
});

// collapse/expand comment
u.addEventForChild(document, 'click', '.togglecomment', function(e, qelem){
  var cid = qelem.getAttribute('data-cid');
  console.log(document.querySelector('#comment-'+cid+' .votecomment'))
  qelem.innerHTML = '[+]';
  if(qelem.classList.contains('collapse')){
    var sty = 'none';
    qelem.classList.remove('collapse');
    qelem.classList.add('expand');
    qelem.parentNode.parentNode.style['margin-left'] = '1.6em';
  } else {
    var sty = 'block'
    qelem.innerHTML = '[–]';
    qelem.classList.add('collapse');
    qelem.classList.remove('expand');
    qelem.parentNode.parentNode.style['margin-left'] = '0';
  }
  document.querySelector('#comment-'+cid+' .votecomment').style.display = sty;
  document.querySelector('#comment-'+cid+' .bottombar').style.display = sty;
  document.querySelector('#comment-'+cid+' .commblock .content').style.display = sty;
  document.querySelector('#child-'+cid).style.display = sty;
})

// reply to comment
u.addEventForChild(document, 'click', '.reply-comment', function(e, qelem){
  var cid = qelem.getAttribute('data-to');
  var pid = qelem.getAttribute('data-pid');
  var back =  document.createElement( "s" );
  back.innerHTML = "reply";
  back.onclick = function(){
    document.querySelector('#rblock-' + cid).outerHTML = ''
    this.parentNode.innerHTML = 'reply'
  };
  qelem.parentNode.parentNode.parentNode.innerHTML += '<div id="rblock-'+cid+'"><div class="cwrap markdown-editor" id="rcomm-'+cid+'"><textarea style="height: 8em;"></textarea></div><div style="display:none" class="error"></div><button class="pure-button pure-button-primary button-xsmall btn-postcomment" data-pid="'+pid+'" data-cid="'+cid+'">Post comment</button> <button class="pure-button button-xsmall btn-preview" data-pvid="rcomm-'+cid+'">Preview</button><div class="cmpreview canclose" style="display:none;"><h4>Comment preview</h4><span class="closemsg">&times;</span><div class="cpreview-content"></div></div></div>';
  initializeEditor(document.querySelector('#rcomm-' + cid));
  var cNode = qelem.cloneNode(false);
  cNode.appendChild(back)
  qelem.parentNode.replaceChild(cNode,qelem );
});

u.addEventForChild(document, 'click', '.btn-postcomment', function(e, qelem){
  var cid = qelem.getAttribute('data-cid');
  var pid = qelem.getAttribute('data-pid');
  var content = document.querySelector('#rcomm-' + cid + ' textarea').value;
  qelem.setAttribute('disabled', true);
  u.post('/do/sendcomment/' + pid, {parent: cid, post: pid, comment: content},
  function(data){
    if (data.status != "ok") {
      qelem.parentNode.querySelector('.error').style.display = 'block';
      qelem.parentNode.querySelector('.error').innerHTML = 'There was an error while editing: ' + data.error;
      qelem.removeAttribute('disabled');
    } else {
      qelem.innerHTML = 'Saved.';
      document.location.reload();
    }
  }, function(){
    qelem.parentNode.querySelector('.error').style.display = 'block';
    qelem.parentNode.querySelector('.error').innerHTML = 'Could not contact the server';
    qelem.removeAttribute('disabled');
  })
});
