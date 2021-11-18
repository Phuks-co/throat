// Post page-related code.
import TextConfirm from './utils/TextConfirm';
import InlinePrompt from './utils/InlinePrompt';
import Icons from './Icon';
import u from './Util';
import initializeEditor from './Editor';
import Tingle from 'tingle.js';
import _ from './utils/I18n';
import socket from './Socket.js'

// Saving/unsaving posts.
u.sub('.savepost', 'click', function (e) {
    const tg = e.currentTarget;
    u.post('/do/save_post/' + tg.getAttribute('data-pid'), {}, function () {
        tg.innerHTML = _('saved');
    });
});

u.sub('.removesavedpost', 'click', function (e) {
    const tg = e.currentTarget;
    u.post('/do/remove_saved_post/' + tg.getAttribute('data-pid'), {}, function () {
        tg.innerHTML = _('removed');
    });
});

u.addEventForChild(document, 'click', '.distinguish', function (e, qelem) {
    function distinguish(admin) {
        u.post('/do/distinguish', {
           cid : qelem.getAttribute('data-cid'),
            pid : qelem.getAttribute('data-pid'),
            as_admin: admin
        },
            function (data) {
                if (data.status != "ok") {
                    e.currentTarget.innerHTML = data.error
                } else {
                    document.location.reload();
                }
            })
        }
    if(qelem.text == _('distinguish') && document.getElementById('pagefoot-admin').getAttribute('data-value') == 'True') {
        InlinePrompt({
            text: _("distinguish as:"),
            options: [
                [_("admin"), () => distinguish(true)],
                [_("mod"), () => distinguish(false)],
            ],
            elem: qelem
        });
    } else {
        distinguish(false)
    }
})

u.addEventForChild(document, 'click', '.delete-post', function (e, qelem) {
    TextConfirm(qelem, function () {
        let reason = "";
        if (qelem.getAttribute('selfdel') != "true") {
            reason = prompt(_('Why are you deleting this?'));
            if (!reason) {
                return false;
            }
        }
        u.post('/do/delete_post', {post: document.getElementById('postinfo').getAttribute('pid'), reason: reason},
            function (data) {
                if (data.status != "ok") {
                    document.getElementById('delpostli').innerHTML = _('Error.');
                } else {
                    document.getElementById('delpostli').innerHTML = _('removed');
                    document.location.reload();
                }
            });
    });
});

u.addEventForChild(document, 'click', '.undelete-post', function (e, qelem) {
    TextConfirm(qelem, function () {
        let reason = "";
        reason = prompt(_('Why are you undeleting this?'));
        if (!reason) {
            return false;
        }
        u.post('/do/undelete_post', {post: document.getElementById('postinfo').getAttribute('pid'), reason: reason},
            function (data) {
                if (data.status != "ok") {
                    document.getElementById('delpostli').innerHTML = _('Error.');
                } else {
                    document.getElementById('delpostli').innerHTML = _('undeleted');
                    document.location.reload();
                }
            });
    });
});

u.addEventForChild(document, 'click', '.browse-history', function (e, qelem) {
  const action = qelem.getAttribute("data-action")
  const content = qelem.parentNode.parentNode;
  const history = content.querySelectorAll('.history')
  const shown = Array.from(history).filter(function(span) {
      return span.style['display'] != 'none'
  })[0]
  const id = parseInt(shown.getAttribute("data-id"))
  let next_id

  if (action == "back") {
    next_id = (id + 1)
  } else {
    next_id = (id - 1)
  }

  history[next_id].style['display'] = ''
  shown.style['display'] = 'none'

  const fwd_button = content.querySelector('.browse-history.forward')
  const back_button = content.querySelector('.browse-history.back')

  if (next_id == 0){
    fwd_button.classList.add('disabled')
    back_button.classList.remove('disabled')
  } else if (next_id == (history.length - 1)) {
    back_button.classList.add('disabled')
    fwd_button.classList.remove('disabled')
  }
  else {
    fwd_button.classList.remove('disabled')
    back_button.classList.remove('disabled')
  }

  content.querySelector('.history-version').innerHTML = (next_id + 1) + '/' + history.length

});

u.addEventForChild(document, 'click', '.edit-title', function (e, qelem) {
    const tg = e.currentTarget;
    TextConfirm(qelem, function () {
        const title = document.querySelector('.post-heading .title').text.trim();
        const reason = prompt(_('New title'), title);
        if (!reason) {
            return false;
        }
        u.post('/do/edit_title', {'reason': reason, 'post': qelem.getAttribute('data-pid')},
            function (data) {
                if (data.status != "ok") {
                    tg.innerHTML = data.error;
                } else {
                    document.location.reload();
                }
            });
    });
});

// Stick post
u.addEventForChild(document, 'click', '.stick-post', function (e, qelem) {
    const parent = qelem.parentNode.parentNode;
    const pid = qelem.parentNode.parentNode.getAttribute('data-pid'), tg = e.currentTarget;
    TextConfirm(qelem, function () {
        u.post('/do/stick/' + pid, {post: document.getElementById('postinfo').getAttribute('pid')},
            function (data) {
                if (data.status != "ok") {
                    alert(data.error);
                } else {
                    tg.innerHTML = _('Done');
                    document.location.reload();
                }
            });
    });
});

// Stick comment
u.addEventForChild(document, 'click', '.stick-comment', function (e, qelem) {
    u.post('/do/stick_comment/' + qelem.getAttribute('data-cid'),
           {post: document.getElementById('postinfo').getAttribute('pid')},
           function (data) {
               if (data.status != "ok") {
                   qelem.innerHTML = data.error;
               } else {
                   document.location.reload();
               }
           });
})

// Sticky post default comment sort
u.addEventForChild(document, 'click', '.sort-comments', function (e, qelem) {
    const parent = qelem.parentNode.parentNode;
    const pid = qelem.parentNode.parentNode.getAttribute('data-pid'), tg = e.currentTarget;
    TextConfirm(qelem, function () {
        u.post('/do/sticky_sort/' + pid, {post: document.getElementById('postinfo').getAttribute('pid')},
            function (data) {
                if (data.status != "ok") {
                    parent.innerHTML = data.error;
                } else {
                    tg.innerHTML = _('Done');
                    document.location.replace(data.redirect);
                }
            });
    });
});

// Lock comments on post.
u.addEventForChild(document, 'click', '.lock-comments', function (e, qelem) {
    const parent = qelem.parentNode.parentNode;
    const pid = qelem.parentNode.parentNode.getAttribute('data-pid'), tg = e.currentTarget;
    TextConfirm(qelem, function () {
        u.post('/do/lock_comments/' + pid, {post: document.getElementById('postinfo').getAttribute('pid')},
            function (data) {
                if (data.status != "ok") {
                    alert(data.error);
                } else {
                    tg.innerHTML = _('Done');
                    document.location.reload();
                }
            });
    });
});

u.addEventForChild(document, 'click', '.announce-post', function (e, qelem) {
    const pid = qelem.parentNode.parentNode.getAttribute('data-pid'), tg = e.currentTarget;
    TextConfirm(qelem, function () {
        u.post('/do/makeannouncement', {post: pid},
            function (data) {
                if (data.status != "ok") {
                    tg.innerHTML = _('Error.');
                } else {
                    tg.innerHTML = _('Done');
                    document.location.reload();
                }
            });
    });
});


u.sub('.editflair', 'click', function () {
    document.getElementById('postflairs').style.display = 'block';
});

u.sub('.selflair', 'click', function () {
    const pid = this.getAttribute('data-pid');
    const flair = this.getAttribute('data-flair');
    const nsub = this.getAttribute('data-sub'), tg = this;
    u.post('/do/flair/' + nsub + '/' + pid + '/' + flair, {post: document.getElementById('postinfo').getAttribute('pid')},
        function (data) {
            if (data.status != "ok") {
                tg.parentNode.innerHTML = _('Error: %1', data.error);
            } else {
                tg.parentNode.innerHTML = _('Done!');
                document.location.reload();
            }
        }
    );
});

u.sub('#remove-flair', 'click', function () {
    const pid = this.getAttribute('data-pid');
    const nsub = this.getAttribute('data-sub'), tg = this;
    u.post('/do/remove_post_flair/' + nsub + '/' + pid, {post: document.getElementById('postinfo').getAttribute('pid')},
        function (data) {
            if (data.status != "ok") {
                tg.innerHTML = _('Error: %1', data.error);
            } else {
                tg.innerHTML = _('Done!');
                document.location.reload();
            }
        }
    );
});


u.addEventForChild(document, 'click', '.nsfw-post', function (e, qelem) {
    const tg = e.currentTarget;
    TextConfirm(qelem, function () {
        u.post('/do/nsfw', {post: document.getElementById('postinfo').getAttribute('pid')},
            function (data) {
                if (data.status != "ok") {
                    tg.innerHTML = _('Error: %1', data.error);
                } else {
                    tg.innerHTML = _('Done!');
                    document.location.reload();
                }
            });
    });
});

u.addEventForChild(document, 'click', '.poll-close', function (e, qelem) {
    const tg = e.currentTarget;
    TextConfirm(qelem, function () {
        u.post('/do/close_poll', {post: document.getElementById('postinfo').getAttribute('pid')},
            function (data) {
                if (data.status != "ok") {
                    tg.innerHTML = _('Error: %1', data.error);
                } else {
                    tg.innerHTML = _('Done!');
                    document.location.reload();
                }
            });
    });
});


// post source
u.addEventForChild(document, 'click', '.post-source', function (e, qelem) {
    const elem = document.getElementById('postcontent');
    const testedit = qelem.parentNode.parentNode.querySelector('.postedit s');
    if (testedit) {
        testedit.click();
    }

    const oc = elem.innerHTML;
    const back = document.createElement("a");
    back.classList.add("postsource");
    back.innerHTML = "<s>" + _('source') + "</s>";
    back.onclick = function () {
        elem.innerHTML = oc;
        this.parentNode.innerHTML = '<a class="post-source">' + _('source') + '</a>';
    };
    const h = elem.clientHeight - 6;
    elem.innerHTML = '<textarea style="height: ' + h + 'px">' + document.getElementById('post-source').innerHTML + '</textarea>';
    qelem.replaceWith(back);
});


// edit post
u.addEventForChild(document, 'click', '.edit-post', function (e, qelem) {
    const elem = document.getElementById('postcontent');
    const testsource = qelem.parentNode.parentNode.querySelector('.postsource s');
    if (testsource) {
        testsource.click();
    }
    const oc = elem.innerHTML;
    const back = document.createElement("a");
    back.classList.add("postedit");
    back.innerHTML = "<s>" + _('edit') + "</s>";
    back.onclick = function () {
        elem.innerHTML = oc;
        back.parentNode.innerHTML = '<a class="edit-post">' + _('edit') + '</a>';
    };
    let h = elem.clientHeight - 6;
    if (h < 100) {
        h = 100;
    }
    elem.innerHTML = '<div id="editpost" class="cwrap markdown-editor"><textarea style="height: ' + h + 'px">' +
        document.getElementById('post-source').innerHTML + '</textarea></div><div style="display:none" class="error">' +
        '</div><button class="pure-button pure-button-primary button-xsmall btn-editpost" data-pid="' + qelem.parentNode.parentNode.getAttribute('data-pid') + '">' +
        _('Save changes') + '</button> <button class="pure-button button-xsmall btn-preview" data-pvid="editpost" >' + _('Preview') + '</button>' +
        '<button class="pure-button button-xsmall btn-rcancel button-transparent" data-pvid="editpost" >' + _('Cancel') + '</button>' +
        '<div class="cmpreview canclose" style="display:none;"><h4>' + _('Comment preview') + '</h4><span class="closemsg">&times;</span><div class="cpreview-content">' +
        '</div></div>';
    elem.querySelector('.btn-rcancel').onclick = back.onclick;
    qelem.replaceWith(back);
    initializeEditor(document.getElementById('editpost'));
    document.querySelector('#editpost textarea').focus();
});


// comment source
u.addEventForChild(document, 'click', '.comment-source', function (e, qelem) {
    const cid = qelem.getAttribute('data-cid');
    const elem = document.getElementById('content-' + cid);

    const testedit = qelem.parentNode.parentNode.querySelector('.edit-comment s');
    if (testedit) {
        testedit.click();
    }
    const oc = elem.innerHTML;
    const back = document.createElement("s");
    back.innerHTML = _("source");
    back.onclick = function () {
        elem.innerHTML = oc;
        this.parentNode.innerHTML = _('source');
    };
    const h = elem.clientHeight + 28;
    elem.innerHTML = '<div class="cwrap"><textarea style="height: ' + h + 'px" readonly>' + document.getElementById('sauce-' + cid).innerHTML + '</textarea></div>';
    const cNode = qelem.cloneNode(false);
    cNode.appendChild(back);
    qelem.parentNode.replaceChild(cNode, qelem);
});

// edit comment
u.addEventForChild(document, 'click', '.edit-comment', function (e, qelem) {
    const cid = qelem.getAttribute('data-cid');
    const elem = document.getElementById('content-' + cid);

    const testsource = qelem.parentNode.parentNode.querySelector('.comment-source s');
    if (testsource) {
        testsource.click();
    }

    const oc = elem.innerHTML;
    const back = document.createElement("s");
    back.innerHTML = _("edit");
    back.onclick = function () {
        elem.innerHTML = oc;
        back.parentNode.innerHTML = _('edit');
    };
    const h = elem.clientHeight + 28;
    elem.innerHTML = '<div class="cwrap markdown-editor" id="ecomm-' + cid + '"><textarea style="height: ' + h + 'px">' +
        document.getElementById('sauce-' + cid).innerHTML + '</textarea></div><div style="display:none" class="error"></div>' +
        '<button class="pure-button pure-button-primary button-xsmall btn-editcomment" data-cid="' + cid + '">' + _('Save changes') + '</button> ' +
        '<button class="pure-button button-xsmall btn-preview" data-pvid="ecomm-' + cid + '">' + _('Preview') + '</button>' +
        '<button class="pure-button button-xsmall btn-rcancel button-transparent" data-pvid="editpost" >' + _('Cancel') + '</button>' +
        '<div class="cmpreview canclose" style="display:none;"><h4>' + _('Comment preview') + '</h4><span class="closemsg">&times;</span>' +
        '<div class="cpreview-content"></div></div>';
    elem.querySelector('.btn-rcancel').onclick = back.onclick;
    const cNode = qelem.cloneNode(false);
    cNode.appendChild(back);
    qelem.parentNode.replaceChild(cNode, qelem);
    initializeEditor(document.getElementById('ecomm-' + cid));
    document.querySelector('#ecomm-' + cid + ' textarea').focus();
});

u.addEventForChild(document, 'click', '.btn-editpost', function (e, qelem) {
    const content = document.querySelector('#editpost textarea').value;
    qelem.setAttribute('disabled', true);
    u.post('/do/edit_txtpost/' + qelem.getAttribute('data-pid'), {content: content},
        function (data) {
            if (data.status != "ok") {
                qelem.parentNode.querySelector('.error').style.display = 'block';
                qelem.parentNode.querySelector('.error').innerHTML = _('There was an error while editing: %1', data.error);
                qelem.removeAttribute('disabled');
            } else {
                qelem.innerHTML = _('Saved.');
                document.location.reload();
            }
        }, function () {
            qelem.parentNode.querySelector('.error').style.display = 'block';
            qelem.parentNode.querySelector('.error').innerHTML = _('Could not contact the server');
            qelem.removeAttribute('disabled');
        });
});

u.addEventForChild(document, 'click', '.btn-editcomment', function (e, qelem) {
    const cid = qelem.getAttribute('data-cid');
    const content = document.querySelector('#ecomm-' + cid + ' textarea').value;
    qelem.setAttribute('disabled', true);
    u.post('/do/edit_comment', {cid: cid, text: content},
        function (data) {
            if (data.status != "ok") {
                qelem.parentNode.querySelector('.error').style.display = 'block';
                qelem.parentNode.querySelector('.error').innerHTML = _('There was an error while editing: %1', data.error);
                qelem.removeAttribute('disabled');
            } else {
                qelem.innerHTML = _('Saved.');
                document.location.reload();
            }
        }, function () {
            qelem.parentNode.querySelector('.error').style.display = 'block';
            qelem.parentNode.querySelector('.error').innerHTML = _('Could not contact the server');
            qelem.removeAttribute('disabled');
        });
});

u.addEventForChild(document, 'click', '.btn-preview', function (e, qelem) {
    let content;
    e.preventDefault();
    if (qelem.getAttribute('data-txid')) {
        content = document.querySelector('#' + qelem.getAttribute('data-txid')).value;
    } else {
        content = document.querySelector('#' + qelem.getAttribute('data-pvid') + ' textarea').value;
    }
    if (content == '') {
        return;
    }
    qelem.setAttribute('disabled', true);
    qelem.innerHTML = _('Loading...');
    u.post('/do/preview', {text: content},
        function (data) {
            if (data.status == "ok") {
                qelem.parentNode.querySelector('.cpreview-content').innerHTML = data.text;
                const title = qelem.parentNode.parentNode.querySelector('#title');
                console.log(title);
                if(title) {
                    const h = document.createElement('h2');
                    h.innerText = title.value;
                    qelem.parentNode.querySelector('.cpreview-content').prepend(document.createElement('hr'));
                    qelem.parentNode.querySelector('.cpreview-content').prepend(h);
                }
                qelem.parentNode.querySelector('.cmpreview').style.display = 'block';
            } else {
                qelem.parentNode.querySelector('.error').style.display = 'block';
                qelem.parentNode.querySelector('.error').innerHTML = _('Error: %1', data.error);
                qelem.removeAttribute('disabled');
            }
            qelem.removeAttribute('disabled');
            qelem.innerHTML = _('Preview');
        }, function () {
            qelem.parentNode.querySelector('.error').style.display = 'block';
            qelem.parentNode.querySelector('.error').innerHTML = _('Could not contact the server');
            qelem.removeAttribute('disabled');
        });
});

// Delete comment
u.addEventForChild(document, 'click', '.delete-comment', function (e, qelem) {
    // confirmation
    const cid = qelem.getAttribute('data-cid'), tg = qelem.parentNode.parentNode;
    TextConfirm(qelem, function () {
        let reason = '';
        if (qelem.getAttribute('selfdel') != "true") {
            reason = prompt(_('Why are you deleting this?'));
            if (!reason) {
                return false;
            }
        }
        u.post('/do/delete_comment', {cid: cid, 'reason': reason},
            function (data) {
                if (data.status != "ok") {
                    tg.innerHTML = _('Error: %1', data.error);
                } else {
                    document.getElementById(cid).classList.add('deleted');
                    tg.innerHTML = '<span class="helper-text">' + _('comment removed') + '</span>';
                }
            });
    });
});

// Un-delete comment
u.addEventForChild(document, 'click', '.undelete-comment', function (e, qelem) {
    // confirmation
    const cid = qelem.getAttribute('data-cid'), tg = qelem;
    TextConfirm(qelem, function () {
        let reason = '';
        reason = prompt(_('Why are you un-deleting this?'));
        if (!reason) {
            return false;
        }
        u.post('/do/undelete_comment', {cid: cid, 'reason': reason},
            function (data) {
                if (data.status != "ok") {
                    tg.parentNode.innerHTML = _('Error: %1', data.error);
                } else {
                    tg.parentNode.innerHTML = _('comment un-deleted');
                    document.location.reload();
                }
            });
    });
});

function setTitle(data) {
    if (data.status == 'error') {
        alert(_('Couldn\'t get title'));
        document.getElementById('graburl').removeAttribute('disabled');
        document.getElementById('graburl').innerHTML = _('Grab title');
    } else {
        document.getElementById('title').value = data.title;
        document.getElementById('graburl').removeAttribute('disabled');
        document.getElementById('graburl').innerHTML = _('Grab again');
    }
}

// This is the id of the title we're waiting for, so if we give up on
// a title grab, and then the user starts a new grab, and then the old
// grab shows up, we can ignore it.
var grabtitleToken = null;

socket.on('grab_title', function(data) {
    if (data.target == grabtitleToken) {
        setTitle(data);
        grabtitleToken = null;
    }
})

// Grab post title from url
u.sub('#graburl', 'click', function (e) {
    e.preventDefault();
    const uri = document.getElementById('link').value;
    if (uri === '') {
        return;
    }
    this.setAttribute('disabled', true);
    this.innerHTML = _('Grabbing...');
    u.post('/do/grabtitle', {u: uri}, function (data) {
        if (data.status == 'deferred') {
            // Subscribe for notification when the title is ready.
            // Set a timer to put up an error alert if the site we are
            // grabbing the title from is unresponsive.
            grabtitleToken = data.token;
            setTimeout(function () {
                if (grabtitleToken == data.token) {
                    grabtitleToken = null;
                    setTitle({status: 'error'});
                }
            }, 15 * 1000);
            socket.emit('deferred', {target: data.token})
        } else {
            setTitle(data)
        }
    });
});


// Tell server which comments have been shown to the user.
const markCommentsSeen = u.debounce(function () {
    const unseenComments = [...document.getElementsByClassName('unseen-comment')];
    let cids = []
    for (let i = 0; i < unseenComments.length; i++) {
        let elem = unseenComments[i];
        if (u.bottomInViewport(elem)) {
            let cid = elem.id.substring("content-".length);
            cids.push(cid);
            elem.classList.remove('unseen-comment');
        }
    }
    if (cids.length > 0) {
        u.post('/do/mark_viewed', {'cids': JSON.stringify(cids)}, function (data) {});
    }
}, false, 250);

window.addEventListener('load', markCommentsSeen);
window.addEventListener('scroll', markCommentsSeen);
window.addEventListener('resize', markCommentsSeen);


// Load children
u.addEventForChild(document, 'click', '.loadchildren', function (e, qelem) {
    qelem.textContent = _("Loading...");
    e.preventDefault();
    u.post('/do/get_children/' + qelem.getAttribute('data-pid') + '/' + qelem.getAttribute('data-cid'), {},
        function (data) {
            qelem.parentNode.innerHTML = data;
            Icons.rendericons();
            markCommentsSeen();
        }, function () {
            qelem.textContent = _("Error.");
        });
});

u.addEventForChild(document, 'click', '.loadsibling', function (e, qelem) {
    let uri;
    qelem.textContent = _("Loading...");
    e.preventDefault();
    const pid = qelem.getAttribute('data-pid');
    const key = qelem.getAttribute('data-key');
    let parent = qelem.getAttribute('data-pcid');
    const sort = qelem.getAttribute('data-sort');
    if (parent == '') {
        parent = 'null';
    }
    if (key === '') {
        uri = '/do/get_children/' + pid + '/' + parent + "?sort=" + sort;
    } else {
        uri = '/do/get_children/' + pid + '/' + parent + '/' + key + "?sort=" + sort;
    }
    window.loading = true;
    u.post(uri, {},
        function (data) {
            window.loading = false;
            qelem.outerHTML = data;
            Icons.rendericons();
            markCommentsSeen();
        }, function () {
            qelem.textContent = _("Error.");
        });
});

// collapse/expand comment
u.addEventForChild(document, 'click', '.togglecomment', function (e, qelem) {
    const cid = qelem.getAttribute('data-cid');
    qelem.innerHTML = '[+]';
    if (qelem.classList.contains('collapse')) {
        qelem.classList.remove('collapse');
        qelem.classList.add('expand');
        if(document.querySelector('#comment-' + cid + ' .votecomment .c-upvote')) {
            document.querySelector('#comment-' + cid + ' .votecomment .c-upvote').classList.add('hidden');
            document.querySelector('#comment-' + cid + ' .votecomment .c-downvote').classList.add('hidden');
        }
        document.querySelector('#comment-' + cid + ' .bottombar').classList.add('hidden');
        if(document.querySelector('#comment-' + cid + ' .replybox')) {
            document.querySelector('#comment-' + cid + ' .replybox').classList.add('hidden');
        }
        document.querySelector('#comment-' + cid + ' .commblock .content').classList.add('hidden');
        document.querySelector('#child-' + cid).classList.add('hidden');
    } else {
        qelem.innerHTML = '[–]';
        qelem.classList.add('collapse');
        qelem.classList.remove('expand');
        if(document.querySelector('#comment-' + cid + ' .votecomment .c-upvote')) {
            document.querySelector('#comment-' + cid + ' .votecomment .c-upvote').classList.remove('hidden');
            document.querySelector('#comment-' + cid + ' .votecomment .c-downvote').classList.remove('hidden');
        }
        document.querySelector('#comment-' + cid + ' .bottombar').classList.remove('hidden');
        if(document.querySelector('#comment-' + cid + ' .replybox')) {
            document.querySelector('#comment-' + cid + ' .replybox').classList.remove('hidden');
        }
        document.querySelector('#comment-' + cid + ' .commblock .content').classList.remove('hidden');
        document.querySelector('#child-' + cid).classList.remove('hidden');
    }
});

// reply to comment
u.addEventForChild(document, 'click', '.reply-comment', function (e, qelem) {
    const cid = qelem.getAttribute('data-to');
    const pid = qelem.getAttribute('data-pid');
    const back = document.createElement("s");
    back.innerHTML = _('reply');
    back.onclick = function () {
        document.querySelector('#rblock-' + cid).outerHTML = '';
        back.parentNode.innerHTML = _('reply');;
    };
    const pN = qelem.parentNode;
    const cNode = qelem.cloneNode(false);
    cNode.appendChild(back);
    pN.replaceChild(cNode, qelem);

    const cs = window.getSelection().anchorNode;
    let pp = "";
    if (cs) {
        if (cs.parentNode.parentNode && cs.parentNode.parentNode.classList.contains('content')) {
            pp = '> ' + window.getSelection().getRangeAt(0).cloneContents().textContent + '\n';
        }
    }

    const lm = document.createElement('div');
    lm.id = 'rblock-' + cid;
    lm.classList.add('replybox');
    lm.innerHTML = '<div class="cwrap markdown-editor" id="rcomm-' + cid + '"><textarea class="exalert" style="height: 8em;"></textarea></div>' +
        '<div style="display:none" class="error"></div><button class="pure-button pure-button-primary button-xsmall btn-postcomment" ' +
        'data-pid="' + pid + '" data-cid="' + cid + '">' + _('Post comment') + '</button> <button class="pure-button button-xsmall btn-preview" data-pvid="rcomm-' +
        cid + '">' + _('Preview') + '</button>' +
        '<button class="pure-button button-xsmall btn-rcancel button-transparent" data-pvid="editpost" >' + _('Cancel') + '</button>' +
        '<div class="cmpreview canclose" style="display:none;"><h4>' + _('Comment preview') + '</h4><span class="closemsg">&times;</span>' +
        '<div class="cpreview-content"></div></div>';
    lm.querySelector('.btn-rcancel').onclick = back.onclick;
    pN.parentNode.parentNode.appendChild(lm);
    initializeEditor(document.querySelector('#rcomm-' + cid));
    document.querySelector('#rcomm-' + cid + ' textarea').focus();
    // pre-populate textarea if there's a comment selected.
    if (pp) {
        const ta = document.querySelector('#rcomm-' + cid + ' textarea');
        ta.value = pp;
        ta.setSelectionRange(ta.value.length, ta.value.length);
    }
});

u.addEventForChild(document, 'click', '.btn-postcomment', function (e, qelem) {
    e.preventDefault();
    const cid = qelem.getAttribute('data-cid');
    const pid = qelem.getAttribute('data-pid');
    const content = document.querySelector('#rcomm-' + cid + ' textarea').value;
    qelem.setAttribute('disabled', true);

    const previewChild = qelem.parentNode.querySelector('.cmpreview');
    previewChild.insertAdjacentHTML('afterend', '<div class="cmpreview canclose" style="display:none;"><h4>' +
                                    _('Comment preview') + '</h4><span class="closemsg">&times;</span>' +
                                    '<div class="cpreview-content"></div></div>');
    qelem.parentNode.removeChild(previewChild);

    window.sending = true;
    let pcid = cid;
    if(pcid[0] == '-') pcid = 0;
    u.post('/do/sendcomment/' + pid, {parent: pcid, post: pid, comment: content},
        function (data) {
            const errorNode = qelem.parentNode.querySelector('.error');
            if (data.status != "ok") {
                errorNode.style.display = 'block';
                errorNode.innerHTML = data.error;
                qelem.removeAttribute('disabled');
            } else {
                errorNode.style.display = 'none';
                const cmtcount = document.getElementById('cmnts');
                window.sending = false;
                if(!cmtcount) {
                    document.querySelector('.reply-comment[data-to="' + cid + '"] s').click();
                    return;
                }
                let count = cmtcount.getAttribute('data-cnt');
                count = count ? count : 0;
                cmtcount.setAttribute('data-cnt', parseInt(count) + 1);
                if (cmtcount.getElementsByTagName('a').length === 0) {
                    const a = document.createElement('a');
                    a.href = '/p/' + pid;
                    a.innerText = _("1 comment");
                    a.id = 'cmnts';
                    cmtcount.innerText = '';
                    cmtcount.appendChild(a);

                } else {
                    const va = cmtcount.getElementsByTagName('a')[0];

                    va.innerText = _("%1 comments", cmtcount.getAttribute('data-cnt'));
                }

                const div = document.createElement('div');
                div.innerHTML = data.comment.trim();

                if (cid == '0') {
                    qelem.removeAttribute('disabled');
                    document.querySelector('#rcomm-' + cid + ' textarea').value = '';
                    if(cmtcount.nextSibling && cmtcount.nextSibling.nextSibling && cmtcount.nextSibling.nextSibling.tagName == 'DIV') {
                        cmtcount.parentNode.insertBefore(div.firstChild, cmtcount.nextSibling.nextSibling.nextSibling);
                    }else{
                        cmtcount.parentNode.insertBefore(div.firstChild, cmtcount.nextSibling);
                    }
                    //document.getElementById(data.cid).scrollIntoView();
                } else {
                    document.querySelector('.reply-comment[data-to="' + cid + '"] s').click();
                    document.getElementById('child-' + cid).prepend(div.firstChild);
                }
                Icons.rendericons();
            }
        }, function (e) {
            qelem.parentNode.querySelector('.error').style.display = 'block';
            if(e.startsWith('{')){
                let err = JSON.parse(e);
                qelem.parentNode.querySelector('.error').innerHTML =err.error[0];
            }else {
                qelem.parentNode.querySelector('.error').innerHTML = _('Could not contact the server ' + e);
            }
            qelem.removeAttribute('disabled');
        });
});

let reportHtml = (data, sub_rules_html) => '<h2>' + _('Report post') + '</h2>' +
    '<p><i>' + _('This report will be forwarded to the site administration') + '</i></p>' +
    '<form class="pure-form pure-form-aligned">' +
    '<div class="pure-control-group">' +
    '<label for="report_reason">' + _('Select a reason to report this post:') + '</label>' +
    '<select name="report_reason" id="report_reason">' +
      '<option value="" disabled selected>' + _('Select one...') + '</option>' +
      '<option value="spam">' + _('SPAM') + '</option>' +
      '<option value="tos">' + _('TOS violation') + '</option>' +
      '<option value="rule">' + _('Sub Rule violation') + '</option>' +
      '<option value="other">' + _('Other') + '</option>' +
    '</select>' +
  '</div>' +
  '<div class="pure-control-group" style="display:none" id="report_rule_set">'+
  '<label for="report_reason">' + _('Which Sub rule did this post violate?') + '</label>' +
    '<select name="report_rule" id="report_rule">' +
      '<option value="" disabled selected>' + _('Select one...') + '</option>' +
      sub_rules_html +
      '<option value="other sub rule">' + _('Other sub rule') + '</option>' +
    '</select>' +
  '</div>' +
  '<div class="pure-control-group" style="display:none" id="report_text_set">'+
    '<label for="report_text">' + _('Explain why you\'re reporting this post:') + '</label>'+
    '<input type="text" name="report_text" id="report_text" style="width:50%" /> '+
  '</div>' +
  '<div class="pure-controls">' +
    '<div style="display:none" class="error">{{error}}</div>' +
    '<button type="button" class="pure-button" id="submit_report" disabled ' + data + '>' + _('Submit') + '</button>' +
  '</div>' +
'</form>';

let report_classes = ['.report-post', '.report-comment']

u.addEventForChild(document, 'click', report_classes, function (e, qelem) {
    const pid = qelem.getAttribute('data-pid');
    const cid = qelem.getAttribute('cid');

    // fetch sub rules
    u.get('/api/v3/sub/rules?pid=' + pid, function(data){
      let rules = [];
      let sub_rules_html = '';
      rules = data.results;

      // set html element for each sub rule
      rules.forEach(function(rule) {
        let rule_html = '<option value="Sub Rule: ' + rule.text + '">' + rule.text + '</option>';
        sub_rules_html = sub_rules_html + rule_html;
        return sub_rules_html
      });

      const modal = new Tingle.modal({});
      // set content
      if (cid) {
        modal.setContent(reportHtml('data-cid=' + cid, 'sub_rules_html=' + sub_rules_html));
      }
      else {
        modal.setContent(reportHtml('data-pid=' + pid, 'sub_rules_html=' + sub_rules_html));
      }
      // open modal
      modal.open();
    });
});

u.addEventForChild(document, 'change', '#report_reason', function (e, qelem) {
    if (qelem.value != '' && qelem.value != 'other' && qelem.value != 'rule') {
        document.getElementById('submit_report').removeAttribute('disabled');
        document.getElementById('report_text_set').style.display = 'none';
        document.getElementById('report_rule_set').style.display = 'none';
    } else if (qelem.value == 'other') {
        if (document.getElementById('report_text').value.length < 3) {
            document.getElementById('submit_report').setAttribute('disabled', 'true');
        }
        document.getElementById('report_text_set').style.display = 'block';
        document.getElementById('report_rule_set').style.display = 'none';
    } else if (qelem.value == 'rule') {
        if (document.getElementById('report_rule').value == '') {
            document.getElementById('submit_report').setAttribute('disabled', 'true');
        }
        if (document.getElementById('report_rule').value == 'other sub rule') {
          document.getElementById('report_rule_set').style.display = 'block';
          document.getElementById('report_text_set').style.display = 'block';
        }
        else {
          document.getElementById('report_text_set').style.display = 'none';
          document.getElementById('report_rule_set').style.display = 'block';
        }
    }
});

u.addEventForChild(document, 'keyup', '#report_text', function (e, qelem) {
    if (qelem.value.length > 3) {
        document.getElementById('submit_report').removeAttribute('disabled');
    } else {
        document.getElementById('submit_report').setAttribute('disabled', 'true');
    }
});

u.addEventForChild(document, 'change', '#report_rule', function (e, qelem) {
  if (qelem.value == 'other sub rule') {
      if (document.getElementById('report_text').value.length < 3) {
          document.getElementById('submit_report').setAttribute('disabled', 'true');
      }
      document.getElementById('report_text_set').style.display = 'block';
  } else if (qelem.value != '') {
    document.getElementById('report_text_set').style.display = 'none';
    document.getElementById('submit_report').removeAttribute('disabled');
  } else {
    document.getElementById('report_text_set').style.display = 'none';
    document.getElementById('submit_report').setAttribute('disabled', 'true');
  }
});


u.addEventForChild(document, 'click', '#submit_report', function (e, qelem) {
    let pid = qelem.getAttribute('data-pid');
    let cid = qelem.getAttribute('data-cid');

    const errorbox = qelem.parentNode.querySelector('.error');

    let send_to_admin = true;
    let reason = document.getElementById('report_reason').value;
    if (reason == 'other') {
        reason = document.getElementById('report_text').value;
    }
    if (reason == 'rule') {
      send_to_admin = false;
      if (document.getElementById('report_rule').value == "other sub rule") {
        reason = "Sub Rule: " + document.getElementById('report_text').value;
      } else {
        reason = document.getElementById('report_rule').value;
      }
    }

    qelem.setAttribute('disabled', true);
    let uri = '/do/report';
    if (cid) {
        pid = qelem.getAttribute('data-cid');
        uri = '/do/report/comment';
    }
    u.post(uri, {post: pid, reason: reason, send_to_admin: send_to_admin},
        function (data) {
            if (data.status != "ok") {
                errorbox.style.display = 'block';
                errorbox.innerHTML = _('Error: ') + data.error;
                qelem.removeAttribute('disabled');
            } else {
                qelem.parentNode.parentNode.parentNode.innerHTML = _('Your report has been sent and will be reviewed by the site administrators.');
            }
        }, function () {
            errorbox.style.display = 'block';
            errorbox.innerHTML = _('Could not contact the server');
            qelem.removeAttribute('disabled');
        });
});


u.addEventForChild(document, 'click', 'a.unblk', function (e, qelem) {
    const sid = qelem.parentNode.parentNode.getAttribute('data-sid');
    TextConfirm(qelem, function () {
        u.post('/do/block/' + sid, {},
            function (data) {
                if (data.status == "ok") {
                    document.location.reload();
                }
            });
    });
});

// Show the comments on a NSFW post when clicked.
u.addEventForChild(document, 'click', '.show-post-comments', function(e, qelem) {
    document.getElementById('post-comments').classList.remove('hide');
    qelem.classList.add('hide');
});

u.addEventForChild(document, 'change', '#flairpicker', function(e, qelem) {
    if (qelem.selectedIndex !== 0) {
        window.location.href = qelem.value;
    }
});
