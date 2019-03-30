""" API endpoints. """

import uuid
from functools import update_wrapper
from datetime import datetime, timedelta
from flask import Blueprint, jsonify, request, render_template, g, current_app, url_for

from peewee import JOIN
from .. import misc
from ..socketio import socketio
from ..models import Sub, User, Grant, Token, Client, SubPost, Sub, SubPostComment, APIToken, APITokenSettings
from ..models import SiteMetadata, SubPostVote, SubMetadata, SubPostCommentVote

api = Blueprint('apiv3', __name__)


@api.route('/getPost/<int:pid>', methods=['get'])
def get_post(pid):
    """Returns information for a post """
    # Same as v2 API but `content` is HTML instead of markdown

    base_query = SubPost.select(SubPost.nsfw, SubPost.content, SubPost.pid, SubPost.title, SubPost.posted, SubPost.score, SubPost.deleted,
                                SubPost.thumbnail, SubPost.link, User.name.alias('user'), Sub.name.alias('sub'), SubPost.flair, SubPost.edited,
                                SubPost.comments, SubPost.ptype, User.status.alias('userstatus'), User.uid, SubPost.upvotes, SubPost.downvotes)
    base_query = base_query.join(User, JOIN.LEFT_OUTER).switch(SubPost).join(Sub, JOIN.LEFT_OUTER)

    post = base_query.where(SubPost.pid == pid).dicts()

    if len(post) == 0:
        return jsonify(status="error", error="Post does not exist")
    
    post = post[0]
    post['deleted'] = True if post['deleted'] != 0 else False
    
    if post['deleted']:  # Clear data for deleted posts
        post['content'] = None
        post['link'] = None
        post['uid'] = None
        post['user'] = '[Deleted]'
        post['thumbnail'] = None
        post['edited'] = None
    
    if post['content']:
        post['content'] = misc.our_markdown(post['content'])
    
    if post['userstatus'] == 10:
        post['user'] = '[Deleted]'
        post['uid'] = None
    del post['userstatus']

    return jsonify(status='ok', post=post)
