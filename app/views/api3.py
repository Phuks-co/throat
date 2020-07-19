""" API endpoints. """

import datetime
import uuid
import re
import requests
from bs4 import BeautifulSoup
from flask import Blueprint, jsonify, request, url_for
from peewee import JOIN, fn
from flask_jwt_extended import JWTManager, jwt_required, create_access_token, create_refresh_token, get_jwt_identity
from flask_jwt_extended import jwt_refresh_token_required, jwt_optional
from .. import misc
from ..auth import auth_provider
from ..socketio import socketio
from ..models import Sub, User, SubPost, SubPostComment, SubMetadata, SubPostCommentVote, SubPostVote, SubSubscriber
from ..models import SiteMetadata, UserMetadata, Message, SubRule, Notification
from ..caching import cache

API = Blueprint('apiv3', __name__)

JWT = JWTManager()


def api_over_limit():
    """ Called when triggering a rate-limit """
    return jsonify(msg="Rate limited. Please try again later"), 429


@API.route('/login', methods=['POST'])
def login():
    """ Logs the user in.
    Parameters (json): username and password
    Returns: access token and refresh token
    """
    if not request.is_json:
        return jsonify(msg="Missing JSON in request"), 400

    username = request.json.get('username', None)
    password = request.json.get('password', None)
    if not username:
        return jsonify(msg="Missing username parameter"), 400
    if not password:
        return jsonify(msg="Missing password parameter"), 400

    try:
        user = User.get(fn.Lower(User.name) == username.lower())
    except User.DoesNotExist:
        return jsonify(msg="Bad username or password"), 401

    if user.status != 0:
        return jsonify(msg="Forbidden"), 403

    if not auth_provider.validate_password(user):
        return jsonify(msg="Bad username or password"), 401

    # Identity can be any data that is json serializable
    access_token = create_access_token(identity=user.uid, fresh=True)
    refresh_token = create_refresh_token(identity=user.uid)
    return jsonify(access_token=access_token, refresh_token=refresh_token, username=user.name), 200


@API.route('/refresh', methods=['POST'])
@jwt_refresh_token_required
def refresh():
    """ Returns a new access token. Requires providing a refresh token """
    current_user = get_jwt_identity()
    try:
        user = User.get_by_id(current_user)
    except User.DoesNotExist:
        return jsonify(msg="User does not exist"), 400

    if user.status != 0:
        return jsonify(msg="Forbidden"), 403

    new_token = create_access_token(identity=current_user, fresh=False)
    return jsonify(access_token=new_token), 200


@API.route('/fresh-login', methods=['POST'])
def fresh_login():
    """ Returns a fresh access token. Requires username and password """
    username = request.json.get('username', None)
    password = request.json.get('password', None)
    try:
        user = User.get(fn.Lower(User.name) == username.lower())
    except User.DoesNotExist:
        return jsonify(msg="Bad username or password"), 401

    if not auth_provider.validate_password(user):
        return jsonify(msg="Bad username or password"), 401

    new_token = create_access_token(identity=user.uid, fresh=True)
    return jsonify(access_token=new_token)


@API.route('/post/<target>', methods=['GET'])
@jwt_optional
def get_post_list(target):
    """ Same as v2, but `content` is returned as parsed markdown and the `sort` can be `default`
    when `target` is a sub """

    if target not in ('all', 'home'):
        sort = request.args.get('sort', default='default')
    else:
        sort = request.args.get('sort', default='new')
    page = request.args.get('page', default=1, type=int)

    if sort not in ('hot', 'top', 'new', 'default'):
        return jsonify(msg="Invalid sort"), 400
    if page < 1:
        return jsonify(msg="Invalid page number"), 400

    uid = get_jwt_identity()
    base_query = SubPost.select(SubPost.nsfw, SubPost.content, SubPost.pid, SubPost.title, SubPost.posted, SubPost.score,
                                SubPost.thumbnail, SubPost.link, User.name.alias('user'), Sub.name.alias('sub'), SubPost.flair, SubPost.edited,
                                SubPost.comments, SubPost.ptype, User.status.alias('userstatus'), User.uid, SubPost.upvotes, *([SubPost.downvotes, SubPostVote.positive] if uid else [SubPost.downvotes]))
    if uid:
        base_query = base_query.join(SubPostVote, JOIN.LEFT_OUTER, on=((SubPostVote.pid == SubPost.pid) & (SubPostVote.uid == uid))).switch(SubPost)
        subs = SubSubscriber.select().where(SubSubscriber.uid == uid)
        subs = subs.order_by(SubSubscriber.order.asc())
        subscribed = [x.sid_id for x in subs if x.status == 1]
        blocked = [x.sid_id for x in subs if x.status == 2]

    base_query = base_query.join(User, JOIN.LEFT_OUTER).switch(SubPost).join(Sub, JOIN.LEFT_OUTER)

    if target == 'all':
        if sort == 'default':
            return jsonify(msg="Invalid sort"), 400
        if uid:
            base_query = base_query.where(SubPost.sid.not_in(blocked))
    elif target == 'home':
        if sort == 'default':
            return jsonify(msg="Invalid sort"), 400

        if not uid:
            base_query = base_query.join(SiteMetadata, JOIN.LEFT_OUTER, on=(SiteMetadata.key == 'default')).where(SubPost.sid == SiteMetadata.value)
        else:
            base_query = base_query.where(SubPost.sid << subscribed)
            base_query = base_query.where(SubPost.sid.not_in(blocked))

    else:
        try:
            sub = Sub.get(fn.Lower(Sub.name) == target.lower())
        except Sub.DoesNotExist:
            return jsonify(msg="Target does not exist"), 404

        if sort == 'default':
            try:
                sort = SubMetadata.get((SubMetadata.sid == sub.sid) & (SubMetadata.key == 'sort'))
                sort = sort.value
            except SubMetadata.DoesNotExist:
                sort = 'hot'

            if sort == 'v':
                sort = 'hot'
            elif sort == 'v_two':
                sort = 'new'
            elif sort == 'v_three':
                sort = 'top'
        base_query = base_query.where(Sub.sid == sub.sid)

    base_query = base_query.where(SubPost.deleted == 0)
    posts = misc.getPostList(base_query, sort, page).dicts()

    cnt = base_query.count() - page * 25
    postList = []
    for post in posts:
        if post['userstatus'] == 10:  # account deleted
            post['user'] = '[Deleted]'
        post['archived'] = (datetime.datetime.utcnow() - post['posted'].replace(tzinfo=None)) > datetime.timedelta(days=config.site.archive_post_after)
        del post['userstatus']
        del post['uid']
        post['content'] = misc.our_markdown(post['content']) if post['ptype'] != 1 else ''
        postList.append(post)

    return jsonify(posts=postList, sort=sort, continues=True if cnt > 0 else False)


@API.route('/post/<sub>/<int:pid>', methods=['GET'])
@jwt_optional
def get_post(sub, pid):
    """Returns information for a post """
    uid = get_jwt_identity()
    base_query = SubPost.select(SubPost.nsfw, SubPost.content, SubPost.pid, SubPost.title, SubPost.posted, SubPost.score, SubPost.deleted,
                                SubPost.thumbnail, SubPost.link, User.name.alias('user'), Sub.name.alias('sub'), SubPost.flair, SubPost.edited,
                                SubPost.comments, SubPost.ptype, User.status.alias('userstatus'), User.uid, SubPost.upvotes, *([SubPost.downvotes, SubPostVote.positive] if uid else [SubPost.downvotes]))

    if uid:
        base_query = base_query.join(SubPostVote, JOIN.LEFT_OUTER, on=((SubPostVote.pid == SubPost.pid) & (SubPostVote.uid == uid))).switch(SubPost)
    base_query = base_query.join(User, JOIN.LEFT_OUTER).switch(SubPost).join(Sub, JOIN.LEFT_OUTER)

    post = base_query.where((SubPost.pid == pid) & (fn.Lower(Sub.name) == sub.lower())).dicts()

    if not post.count():
        return jsonify(msg="Post does not exist"), 404

    post = post[0]
    post['deleted'] = True if post['deleted'] != 0 else False

    if post['deleted']:  # Clear data for deleted posts
        post['content'] = None
        post['link'] = None
        post['uid'] = None
        post['user'] = '[Deleted]'
        post['thumbnail'] = None
        post['edited'] = None

    post['source'] = post['content']
    if post['content']:
        post['content'] = misc.our_markdown(post['content'])

    if post['userstatus'] == 10:
        post['user'] = '[Deleted]'

    post['archived'] = (datetime.datetime.utcnow() - post['posted'].replace(tzinfo=None)) > datetime.timedelta(days=config.site.archive_post_after)
    if post['ptype'] == 0:
        post['type'] = 'text'
    elif post['ptype'] == 1:
        post['type'] = 'link'
    elif post['ptype'] == 2:
        post['type'] = 'upload'
    elif post['ptype'] == 3:
        post['type'] = 'poll'
    del post['ptype']
    del post['userstatus']
    del post['uid']

    return jsonify(post=post)


@API.route('/post/<sub>/<int:pid>', methods=['PATCH'])
@jwt_required
def edit_post(sub, pid):
    uid = get_jwt_identity()
    content = request.json.get('content', None)
    if not content:
        return jsonify(msg="Content parameter required"), 400

    if len(content) > 16384:
        return jsonify(msg="Content is too long"), 400

    try:
        post = SubPost.select().join(Sub, JOIN.LEFT_OUTER).where(
            (SubPost.pid == pid) & (fn.Lower(Sub.name) == sub.lower()))
        post = post.where(SubPost.deleted == 0).get()
    except SubPost.DoesNotExist:
        return jsonify(msg="Post does not exist"), 404

    if post.uid_id != uid:
        return jsonify(msg="Unauthorized"), 403

    if misc.is_sub_banned(sub, uid=uid):
        return jsonify(msg='You are banned on this sub.'), 403

    if (datetime.datetime.utcnow() - post.posted.replace(tzinfo=None)) > datetime.timedelta(days=config.site.archive_post_after):
        return jsonify(msg='Post is archived'), 403

    post.content = content
    # Only save edited time if it was posted more than five minutes ago
    if (datetime.datetime.utcnow() - post.posted.replace(tzinfo=None)).seconds > 300:
        post.edited = datetime.datetime.utcnow()
    post.save()
    return get_post(sub, pid)


@API.route('/post/<sub>/<int:pid>', methods=['DELETE'])
@jwt_required
def delete_post(sub, pid):
    uid = get_jwt_identity()
    try:
        post = SubPost.select().join(Sub, JOIN.LEFT_OUTER).where(
            (SubPost.pid == pid) & (fn.Lower(Sub.name) == sub.lower()))
        post = post.where(SubPost.deleted == 0).get()
    except SubPost.DoesNotExist:
        return jsonify(msg="Post does not exist"), 404

    # TODO: Implement admin logic in the api
    if not misc.is_sub_mod(uid, post.sid_id, 2) and post.uid_id != uid:
        return jsonify(msg="Unauthorized"), 403

    if post.uid_id == uid:
        post.deleted = 1
    else:
        reason = request.args.get('reason', default=None)
        if not reason:
            return jsonify(msg="Cannot delete post without reason"), 400
        post.deleted = 2
        # TODO: Make this a translatable notification
        Notification(type='POST_DELETE', sub=post.sid, post=post.pid, content='Reason: ' + reason,
                     sender=uid, target=post.uid).save()

        misc.create_sublog(misc.LOG_TYPE_SUB_DELETE_POST, uid, post.sid,
                           comment=reason, link=url_for('site.view_post_inbox', pid=post.pid),
                           admin=False)

    if (datetime.datetime.utcnow() - post.posted.replace(tzinfo=None)).seconds < 86400:
        socketio.emit('deletion', {'pid': post.pid}, namespace='/snt', room='/all/new')

    # check if the post is an announcement. Unannounce if it is.
    try:
        ann = SiteMetadata.select().where(SiteMetadata.key == 'announcement').where(
            SiteMetadata.value == post.pid).get()
        ann.delete_instance()
        cache.delete_memoized(misc.getAnnouncementPid)
    except SiteMetadata.DoesNotExist:
        pass
    post.save()
    Sub.update(posts=Sub.posts - 1).where(Sub.sid == post.sid).execute()
    return jsonify(), 200


@API.route('/post/<sub>/<int:pid>/vote', methods=['POST'])
@jwt_required
def vote_post(sub, pid):
    """ Logs an upvote to a post. """
    uid = get_jwt_identity()
    value = request.json.get('upvote', None)
    if type(value) is not bool:
        return jsonify(msg="Upvote must be true or false")

    return misc.cast_vote(uid, "post", pid, value)


@API.route('/post/<sub>/<int:pid>/comment', methods=['GET'])
@jwt_optional
def get_post_comments(sub, pid):
    """ Returns comment tree

    Return dict format:
    "comments": [
        {"cid": ...,
            "content": ...,
            "children": [
                {"cid": ..., ...},
                ...
                {"cid": null}
            ]
        },
        ....
        {"cid": null, "key": ...} <-- "Load more comments" (siblings) mark
    ]

    Upon reaching a cid=null comment, return link to get_post_comment_children with
    cid of the parent comment or 0 if it is a root comment and lim equal to the key
    provided or absent if no key is provided
    """
    current_user = get_jwt_identity()
    try:
        post = SubPost.get(SubPost.pid == pid)
    except SubPost.DoesNotExist:
        return jsonify(msg="Post does not exist"), 404

    # 1 - Fetch all comments (only cid and parentcid)
    comments = SubPostComment.select(SubPostComment.cid, SubPostComment.parentcid).where(SubPostComment.pid == post.pid).order_by(SubPostComment.score.desc()).dicts()
    if not comments.count():
        return jsonify(comments=[])

    comment_tree = misc.get_comment_tree(comments, uid=current_user)
    return jsonify(comments=comment_tree)


@API.route('/post/<sub>/<int:pid>/comment', methods=['POST'])
@jwt_required
@misc.ratelimit(1, per=30, over_limit=api_over_limit)  # Once every 30 secs
def create_comment(sub, pid):
    uid = get_jwt_identity()
    if not request.is_json:
        return jsonify(msg="Missing JSON in request"), 400

    parentcid = request.json.get('parentcid', None)
    content = request.json.get('content', None)

    if not content:
        return jsonify(msg='Missing required parameters'), 400

    try:
        user = User.get(User.uid == uid)
    except User.DoesNotExist:
        return jsonify(msg="Unknown error. User disappeared"), 403

    try:
        post = SubPost.get(SubPost.pid == pid)
    except SubPost.DoesNotExist:
        return jsonify(msg='Post does not exist'), 404
    if post.deleted:
        return jsonify(msg='Post was deleted'), 404

    if (datetime.datetime.utcnow() - post.posted.replace(tzinfo=None)) > datetime.timedelta(days=config.site.archive_post_after):
        return jsonify(msg="Post is archived"), 403

    try:
        SubMetadata.get((SubMetadata.sid == post.sid) & (SubMetadata.key == "ban") & (SubMetadata.value == user.uid))
        return jsonify(msg='You are banned on this sub.'), 403
    except SubMetadata.DoesNotExist:
        pass

    if len(content) > 16384:
        return jsonify(msg="Content is too long"), 400

    if parentcid:
        try:
            parent = SubPostComment.get(SubPostComment.cid == parentcid)
        except SubPostComment.DoesNotExist:
            return jsonify(msg="Parent comment does not exist"), 404

        if parent.status is not None or parent.pid.pid != post.pid:
            return jsonify(msg="Parent comment does not exist"), 404
    else:
        parentcid = None

    comment = SubPostComment.create(pid=pid, uid=uid,
                                    content=content,
                                    parentcid=parentcid,
                                    time=datetime.datetime.utcnow(),
                                    cid=uuid.uuid4(), score=0, upvotes=0, downvotes=0)

    SubPost.update(comments=SubPost.comments + 1).where(SubPost.pid == post.pid).execute()
    comment.save()

    socketio.emit('threadcomments', {'pid': post.pid, 'comments': post.comments + 1},
                  namespace='/snt', room=post.pid)

    # 5 - send pm to parent
    if parentcid:
        parent = SubPostComment.get(SubPostComment.cid == parentcid)
        notif_to = parent.uid_id
        ntype = 'COMMENT_REPLY'
    else:
        notif_to = post.uid_id
        ntype = 'POST_REPLY'

    if notif_to != uid and uid not in misc.get_ignores(notif_to):
        Notification(type=ntype, sub=post.sid, post=post.pid, comment=comment.cid,
                     sender=uid, target=notif_to).save()
        socketio.emit('notification', {'count': misc.get_notification_count(notif_to)},
                      namespace='/snt', room='user' + notif_to)

    # 6 - Process mentions
    sub = Sub.get_by_id(post.sid)
    misc.workWithMentions(content, notif_to, post, sub, cid=comment.cid, c_user=user)

    # Return the comment data
    comm = SubPostComment.select(SubPostComment.cid, SubPostComment.content, SubPostComment.lastedit,
                                 SubPostComment.score, SubPostComment.status, SubPostComment.time, SubPostComment.pid,
                                 User.name.alias('user'), SubPostCommentVote.positive, User.status.alias('userstatus'),
                                 SubPostComment.upvotes, SubPostComment.downvotes) \
        .join(User, on=(User.uid == SubPostComment.uid)).switch(SubPostComment) \
        .join(SubPostCommentVote, JOIN.LEFT_OUTER, on=((SubPostCommentVote.uid == uid) &
                                                       (SubPostCommentVote.cid == SubPostComment.cid))) \
        .where(SubPostComment.cid == comment.cid).dicts()[0]
    comm['source'] = comm['content']
    comm['content'] = misc.our_markdown(comm['content'])
    return jsonify(comment=comm), 200


@API.route('/post/<sub>/<int:pid>/comment/<cid>', methods=['PATCH'])
@jwt_required
def edit_comment(sub, pid, cid):
    """ Edits a comment """
    uid = get_jwt_identity()
    if not request.is_json:
        return jsonify(msg="Missing JSON in request"), 400

    content = request.json.get('content', None)
    if not content:
        return jsonify(msg="Content parameter required"), 400

    # Fetch the comment
    try:
        comment = SubPostComment.get((SubPostComment.pid == pid) & (SubPostComment.cid == cid))
    except SubPostComment.DoesNotExist:
        return jsonify(msg="Comment not found"), 404

    if comment.uid_id != uid:
        return jsonify(msg="Unauthorized"), 403

    if (datetime.datetime.utcnow() - comment.pid.posted.replace(tzinfo=None)) > datetime.timedelta(days=config.site.archive_post_after):
        return jsonify(msg="Post is archived"), 400

    if len(content) > 16384:
        return jsonify(msg="Content is too long"), 400

    comment.content = content
    comment.lastedit = datetime.datetime.utcnow()
    comment.save()
    # TODO: move this block to a function
    comm = SubPostComment.select(SubPostComment.cid, SubPostComment.content, SubPostComment.lastedit,
                                 SubPostComment.score, SubPostComment.status, SubPostComment.time, SubPostComment.pid,
                                 User.name.alias('user'), SubPostCommentVote.positive, User.status.alias('userstatus'),
                                 SubPostComment.upvotes, SubPostComment.downvotes) \
        .join(User, on=(User.uid == SubPostComment.uid)).switch(SubPostComment) \
        .join(SubPostCommentVote, JOIN.LEFT_OUTER, on=((SubPostCommentVote.uid == uid) &
                                                       (SubPostCommentVote.cid == SubPostComment.cid))) \
        .where(SubPostComment.cid == comment.cid).dicts()[0]
    comm['source'] = comm['content']
    comm['content'] = misc.our_markdown(comm['content'])
    return jsonify(comment=comm), 200


@API.route('/post/<sub>/<int:pid>/comment/<cid>', methods=['DELETE'])
@jwt_required
def delete_comment(sub, pid, cid):
    uid = get_jwt_identity()

    # Fetch the comment
    try:
        comment = SubPostComment.get((SubPostComment.pid == pid) & (SubPostComment.cid == cid))
    except SubPostComment.DoesNotExist:
        return jsonify(msg="Comment not found"), 404

    if comment.uid_id != uid:
        return jsonify(msg="Unauthorized"), 403

    if (datetime.datetime.utcnow() - comment.pid.posted.replace(tzinfo=None)) > datetime.timedelta(days=config.site.archive_post_after):
        return jsonify(msg="Post is archived"), 400

    comment.status = 1
    comment.save()

    q = Message.delete().where(Message.mlink == cid)
    q.execute()
    return jsonify(), 200


@API.route('/post/<sub>/<int:pid>/comment/<cid>/vote', methods=['POST'])
@jwt_required
def vote_comment(sub, pid, cid):
    """ Logs an upvote to a post. """
    uid = get_jwt_identity()
    value = request.json.get('upvote', None)
    if type(value) is not bool:
        return jsonify(msg="Upvote must be true or false"), 400

    return misc.cast_vote(uid, "comment", cid, value)


@API.route('/post/<sub>/<int:pid>/comment/<cid>/children', methods=['GET'])
def get_post_comment_children(sub, pid, cid):
    """ if key is not present, load all children for cid.
    if key is present, load all comments after (???) index `key`

    NOTE: This is a crappy solution since comment sorting might change when user is
    seeing the page and we might end up re-sending a comment (will show as duplicate).
    This can be solved by the front-end checking if a cid was already rendered, but it
    is a horrible solution
    """
    lim = request.args.get('key', default='')
    try:
        post = SubPost.get(SubPost.pid == pid)
    except SubPost.DoesNotExist:
        return jsonify(msg='Post does not exist'), 404
    if cid == 'null':
        cid = '0'
    if cid != '0':
        try:
            root = SubPostComment.get(SubPostComment.cid == cid)
            if root.pid_id != post.pid:
                return jsonify(msg='Comment does not belong to the given post'), 400
        except SubPostComment.DoesNotExist:
            return jsonify(msg='Post does not exist'), 404

    comments = SubPostComment.select(SubPostComment.cid, SubPostComment.parentcid).where(SubPostComment.pid == pid).order_by(SubPostComment.score.desc()).dicts()
    if not comments.count():
        return jsonify(comments=[])

    if lim:
        if cid == '0':
            cid = None
        comment_tree = misc.get_comment_tree(comments, cid, lim)
    elif cid != '0':
        comment_tree = misc.get_comment_tree(comments, cid)
    else:
        return jsonify(msg='Illegal comment id'), 400
    return jsonify(comments=comment_tree)


class ChallengeRequired(Exception):
    """ Raised when a challenge is required. Catched by the error handlers below """
    pass


class ChallengeWrong(Exception):
    """ Raised when a challenge's solution is wrong. Catcher by the error handlers below """
    pass


@API.errorhandler(ChallengeRequired)
def chall_required(error):
    return jsonify(msg="Challenge required"), 423


@API.errorhandler(ChallengeWrong)
def chall_wrong(error):
    return jsonify(msg="Invalid response", failed=True), 423


def check_challenge():
    challenge_token = request.json.get('challengeToken')
    challenge_response = request.json.get('challengeResponse')

    if not challenge_token or not challenge_response:
        misc.reset_ratelimit(30)
        raise ChallengeRequired

    if not misc.validate_captcha(challenge_token, challenge_response):
        misc.reset_ratelimit(30)
        raise ChallengeWrong

    return True


@API.route('/challenge', methods=['GET'])
@jwt_required
def get_challenge():
    challenge = misc.create_captcha()
    return jsonify(challenge_token=challenge[0], challenge_blob=challenge[1])


@API.route('/post', methods=['POST'])
@jwt_required
@misc.ratelimit(1, per=30, over_limit=api_over_limit)  # Once every 30 secs
def create_post():
    uid = get_jwt_identity()
    if not request.is_json:
        return jsonify(msg="Missing JSON in request"), 400

    sub = request.json.get('sub', None)
    ptype = request.json.get('type', None)
    title = request.json.get('title', None)
    link = request.json.get('link', None)
    content = request.json.get('content', None)
    nsfw = request.json.get('nsfw', False)

    if not sub or ptype is None or not title:
        return jsonify(msg='Missing required parameters'), 400

    if ptype not in ('link', 'upload', 'text', 'poll'):
        return jsonify(msg='Illegal value for ptype'), 400

    # TODO: Polls, uploads
    if ptype in ('poll', 'upload'):
        return jsonify(msg='This method does not support poll creation'), 400

    try:
        user = User.get(User.uid == uid)
    except User.DoesNotExist:
        return jsonify(msg="Unknown error. User disappeared"), 403

    try:  # TODO: Exception for admins
        enable_posting = SiteMetadata.get(SiteMetadata.key == 'enable_posting')
        if enable_posting.value in ('False', '0'):
            return jsonify(msg="Posting has been temporarily disabled"), 400
    except SiteMetadata.DoesNotExist:
        pass

    try:
        sub = Sub.get(fn.Lower(Sub.name) == sub.lower())
    except Sub.DoesNotExist:
        return jsonify(msg="Sub does not exist"), 404

    if sub.name.lower() in ('all', 'new', 'hot', 'top', 'admin', 'home'):  # TODO: Make this a blacklist setting in the config file?
        return jsonify(msg="You can't post on this sub"), 403

    subdata = misc.getSubData(sub.sid, simple=True)

    if misc.is_sub_banned(sub, uid=uid):
        return jsonify(msg="You're banned from this sub"), 403

    if subdata.get('restricted', 0) == '1':
        return jsonify(msg='Only moderators can post on this sub'), 403

    if len(title.strip(misc.WHITESPACE)) < 3:
        return jsonify(msg='Post title is too short'), 400

    if len(title) > 350:
        return jsonify(msg='Post title is too long'), 400

    if misc.get_user_level(uid)[0] < 7:
        today = datetime.datetime.utcnow() - datetime.timedelta(days=1)
        lposts = SubPost.select().where(SubPost.uid == uid).where(SubPost.sid == sub.sid).where(SubPost.posted > today).count()
        tposts = SubPost.select().where(SubPost.uid == uid).where(SubPost.posted > today).count()
        if lposts > 10 or tposts > 25:
            return jsonify(msg="You have posted too much today"), 403
    post_type = 0
    if ptype == 'link':
        post_type = 1
        if not link:
            return jsonify(msg='No link provided'), 400

        if content:
            return jsonify(msg='Link posts do not accept content'), 400

        if misc.is_domain_banned(link):
            return jsonify(msg="Link's domain is banned"), 400

        recent = datetime.datetime.utcnow() - datetime.timedelta(days=5)
        try:
            wpost = SubPost.select().where(SubPost.sid == sub.sid).where(SubPost.link == link)
            wpost.where(SubPost.deleted == 0).where(SubPost.posted > recent).get()
            return jsonify(msg="This link has already been posted recently on this sub"), 403
        except SubPost.DoesNotExist:
            pass
    elif ptype == 'text':
        post_type = 0
        if link:
            return jsonify(msg='Text posts do not accept link'), 400
        if len(content) > 16384:
            return jsonify(msg='Post content is too long'), 400

    if misc.get_user_level(user.uid)[0] <= 4:
        check_challenge()

    post = SubPost.create(sid=sub.sid,
                          uid=uid,
                          title=title.strip(misc.WHITESPACE),
                          content=content,
                          link=link if ptype == 'link' else None,
                          posted=datetime.datetime.utcnow(),
                          score=1, upvotes=1, downvotes=0, deleted=0, comments=0,
                          ptype=post_type,
                          nsfw=nsfw if not subdata.get('nsfw') == '1' else 1,
                          thumbnail=misc.get_thumbnail(link) if ptype == 'link' else '')

    Sub.update(posts=Sub.posts + 1).where(Sub.sid == sub.sid).execute()
    addr = url_for('sub.view_post', sub=sub.name, pid=post.pid)
    posts = misc.getPostList(misc.postListQueryBase(nofilter=True).where(SubPost.pid == post.pid), 'new', 1).dicts()
    socketio.emit('thread',
                  {'addr': addr, 'sub': sub.name, 'type': post_type,
                   'user': user.name, 'pid': post.pid, 'sid': sub.sid,
                   'html': misc.engine.get_template('shared/post.html').render({'posts': posts, 'sub': False})},
                  namespace='/snt', room='/all/new')

    SubPostVote.create(uid=uid, pid=post.pid, positive=True)
    User.update(given=User.given + 1).where(User.uid == uid).execute()

    misc.workWithMentions(content, None, post, sub, c_user=user)
    misc.workWithMentions(title, None, post, sub, c_user=user)

    socketio.emit('yourvote', {'pid': post.pid, 'status': 1, 'score': post.score}, namespace='/snt',
                  room='user' + user.name)

    return jsonify(status='ok', pid=post.pid, sub=sub.name)


@API.route('/sub', methods=['GET'])
def search_sub():
    query = request.args.get('query', '')
    if len(query) < 3 or not misc.allowedNames.match(query):
        return jsonify(results=[])

    query = '%' + query + '%'
    subs = Sub.select(Sub.name).where(Sub.name ** query).limit(10).dicts()

    return jsonify(results=list(subs))

@API.route('/sub/rules', methods=['GET'])
def get_sub_rules():
    pid = request.args.get('pid', '')
    sub = SubPost.select().where(SubPost.pid == pid).join(Sub).where(Sub.sid == SubPost.sid).dicts().get()
    rules = list(SubRule.select().where(SubRule.sid == sub['sid']).dicts())

    return jsonify(results=rules)


@API.route('/user/settings', methods=['GET'])
@jwt_required
def get_settings():
    """ Returns account settings """
    uid = get_jwt_identity()
    prefs = UserMetadata.select().where(UserMetadata.uid == uid)
    prefs = prefs.where(UserMetadata.key << ('labrat', 'nostyles', 'nsfw', 'nochat'))
    prefs = {x.key: x.value for x in prefs}
    return jsonify(settings={
        "labrat": True if prefs.get('labrat', False) == '1' else False,
        "nostyles": True if prefs.get('nostyles', False) == '1' else False,
        "nsfw": True if prefs.get('nsfw', False) == '1' else False,
        "nochat": True if prefs.get('nochat', False) == '1' else False,
    })


@API.route('/user/settings', methods=['POST'])
@jwt_required
def set_settings():
    """ Changes accounts settings (excl. password/email)
    Required post parameters: settings (dict of setting options and values).
    Accepted settings options:
    labrat (bool), nostyles (bool), shownsfw (bool), nochat (bools)
    """
    uid = get_jwt_identity()
    if not request.is_json:
        return jsonify(msg="Missing JSON in request"), 400

    settings = request.json.get('settings', None)
    if not settings:
        return jsonify(msg="Missing parameters"), 400

    if [x for x in settings.keys() if x not in ['labrat', 'nostyles', 'nsfw', 'nochat']]:
        return jsonify(msg="Invalid setting options sent"), 400

    # Apply settings
    qrys = []
    for sett in settings:
        value = settings[sett]
        if sett in ['labrat', 'nostyles', 'nsfw', 'nochat']:
            if not isinstance(settings[sett], bool):
                return jsonify(msg="Invalid type for setting"), 400
            value = '1' if value else '0'


        qrys.append(UserMetadata.update(value=value).where((UserMetadata.key == sett) & (UserMetadata.uid == uid)))

    [x.execute() for x in qrys]
    return jsonify()


@API.route('/grabtitle', methods=['GET'])
@jwt_required
def grab_title():
    url = request.args.get('url', None)
    if not url:
        return jsonify(msg='url parameter required'), 400

    try:
        req = misc.safeRequest(url)
    except (requests.exceptions.RequestException, ValueError):
        return jsonify(msg="Couldn't fetch title"), 400

    og = BeautifulSoup(req[1], 'lxml', from_encoding='utf-8')
    try:
        title = og('title')[0].text
    except (OSError, ValueError, IndexError):
        return jsonify(msg="Couldn't fetch title"), 400

    title = title.strip(misc.WHITESPACE)
    title = re.sub(' - Youtube$', '', title)
    return jsonify(title=title), 200
