""" API endpoints. """

import datetime
import uuid
import bcrypt
from flask import Blueprint, jsonify, request, url_for
from peewee import JOIN
from flask_jwt_extended import JWTManager, jwt_required, create_access_token, create_refresh_token, get_jwt_identity
from flask_jwt_extended import jwt_refresh_token_required, jwt_optional
from .. import misc
from ..socketio import socketio
from ..models import Sub, User, SubPost, SubPostComment, SubMetadata, SubPostCommentVote, SubPostVote, SubSubscriber
from ..models import SiteMetadata

API = Blueprint('apiv3', __name__)

JWT = JWTManager()


def api_over_limit(limit):
    """ Called when triggering a rate-limit """
    return jsonify(msg="Rate limited. Please try again ({0} every {1}s)".format(limit.limit, limit.per)), 429


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
        user = User.get(User.name == username)
    except User.DoesNotExist:
        return jsonify(msg="Bad username or password"), 401

    if user.crypto == 1:  # bcrypt
        thash = bcrypt.hashpw(password.encode('utf-8'),
                              user.password.encode('utf-8'))
        if thash != user.password.encode('utf-8'):
            return jsonify(msg="Bad username or password"), 401
    else:
        return jsonify(msg="Bad user data"), 400

    # Identity can be any data that is json serializable
    access_token = create_access_token(identity=user.uid, fresh=True)
    refresh_token = create_refresh_token(identity=user.uid)
    return jsonify(access_token=access_token, refresh_token=refresh_token), 200


@API.route('/refresh', methods=['POST'])
@jwt_refresh_token_required
def refresh():
    """ Returns a new access token. Requires providing a refresh token """
    current_user = get_jwt_identity()
    new_token = create_access_token(identity=current_user, fresh=False)
    return jsonify(access_token=new_token), 200


@API.route('/fresh-login', methods=['POST'])
def fresh_login():
    """ Returns a fresh access token. Requires username and password """
    username = request.json.get('username', None)
    password = request.json.get('password', None)
    try:
        user = User.get(User.name == username)
    except User.DoesNotExist:
        return jsonify(msg="Bad username or password"), 401

    if user.crypto == 1:  # bcrypt
        thash = bcrypt.hashpw(password.encode('utf-8'),
                              user.password.encode('utf-8'))
        if thash != user.password.encode('utf-8'):
            return jsonify(msg="Bad username or password"), 401
    else:
        return jsonify(msg="Bad user data"), 400

    new_token = create_access_token(identity=user.uid, fresh=True)
    return jsonify(access_token=new_token)


@API.route('/getPost/<int:pid>', methods=['get'])
@jwt_optional
def get_post(pid):
    """Returns information for a post """
    # Same as v2 API but `content` is HTML instead of markdown
    uid = get_jwt_identity()
    base_query = SubPost.select(SubPost.nsfw, SubPost.content, SubPost.pid, SubPost.title, SubPost.posted, SubPost.score, SubPost.deleted,
                                SubPost.thumbnail, SubPost.link, User.name.alias('user'), Sub.name.alias('sub'), SubPost.flair, SubPost.edited,
                                SubPost.comments, SubPost.ptype, User.status.alias('userstatus'), User.uid, SubPost.upvotes, *([SubPost.downvotes, SubPostVote.positive] if uid else [SubPost.downvotes]))

    if uid:
        base_query = base_query.join(SubPostVote, JOIN.LEFT_OUTER, on=((SubPostVote.pid == SubPost.pid) & (SubPostVote.uid == uid))).switch(SubPost)
    base_query = base_query.join(User, JOIN.LEFT_OUTER).switch(SubPost).join(Sub, JOIN.LEFT_OUTER)

    post = base_query.where(SubPost.pid == pid).dicts()

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

    if post['content']:
        post['content'] = misc.our_markdown(post['content'])

    if post['userstatus'] == 10:
        post['user'] = '[Deleted]'
        post['uid'] = None
    del post['userstatus']

    return jsonify(post=post)


def get_comment_tree(comments, root=None, only_after=None, uid=None):
    """ Returns a fully paginated and expanded comment tree.

    Parameters:
        comments: bare list of comments (only cid and parentcid)
        root: if present, the root comment to start building the tree on
        only_after: removes all siblings of `root` after the cid on its value

    TODO: Move to misc and implement globally
    """
    def build_tree(tuff, root=None):
        """ Builds a comment tree """
        res = []
        for i in tuff[::]:
            if i['parentcid'] == root:
                tuff.remove(i)
                i['children'] = build_tree(tuff, root=i['cid'])
                res.append(i)
        return res

    # 2 - Build bare comment tree
    comment_tree = build_tree(list(comments))

    # 2.1 - get only a branch of the tree if necessary
    if root:
        def select_branch(comments, root):
            """ Finds a branch with a certain root and returns a new tree """
            for i in comments:
                if i['cid'] == root:
                    return i
                k = select_branch(i['children'], root)
                if k:
                    return k
        comment_tree = select_branch(comment_tree, root)
        if comment_tree:
            # include the parent of the root for context.
            if comment_tree['parentcid'] is None:
                comment_tree = [comment_tree]
            else:
                orig_root = [x for x in list(comments) if x['cid'] == comment_tree['parentcid']]
                orig_root[0]['children'] = [comment_tree]
                comment_tree = orig_root
        else:
            return []
    # 3 - Trim tree (remove all children of depth=3 comments, all siblings after #5
    cid_list = []
    trimmed = False
    def recursive_check(tree, depth=0, trimmed=None):
        """ Recursively checks tree to apply pagination limits """
        or_len = len(tree)
        if only_after and not trimmed:
            imf = list(filter(lambda i: i['cid'] == only_after, tree))
            if imf:
                try:
                    tree = tree[tree.index(imf[0]) + 1:]
                except IndexError:
                    return []
                or_len = len(tree)
                trimmed = True
        if depth > 3:
            return [{'cid': None, 'more': len(tree)}] if tree else []
        if (len(tree) > 5 and depth > 0) or (len(tree) > 10):
            tree = tree[:6] if depth > 0 else tree[:11]
            tree.append({'cid': None, 'key': tree[-1]['cid'], 'more': or_len - len(tree)})

        for i in tree:
            if not i['cid']:
                continue
            cid_list.append(i['cid'])
            i['children'] = recursive_check(i['children'], depth+1)

        return tree
    import pprint
    pprint.pprint(comment_tree)

    comment_tree = recursive_check(comment_tree, trimmed=trimmed)

    # 4 - Populate the tree (get all the data and cram it into the tree)
    expcomms = SubPostComment.select(SubPostComment.cid, SubPostComment.content, SubPostComment.lastedit,
                                     SubPostComment.score, SubPostComment.status, SubPostComment.time, SubPostComment.pid,
                                     User.name.alias('user'), *([SubPostCommentVote.positive, SubPostComment.uid] if uid else [SubPostComment.uid]), # silly hack
                                     User.status.alias('userstatus'), SubPostComment.upvotes, SubPostComment.downvotes)
    expcomms = expcomms.join(User, on=(User.uid == SubPostComment.uid)).switch(SubPostComment)
    if uid:
        expcomms = expcomms.join(SubPostCommentVote, JOIN.LEFT_OUTER, on=((SubPostCommentVote.uid == uid) & (SubPostCommentVote.cid == SubPostComment.cid)))
    expcomms = expcomms.where(SubPostComment.cid << cid_list).dicts()

    commdata = {}
    for comm in expcomms:
        if comm['userstatus'] == 10 or comm['status']:
            comm['user'] = '[Deleted]'
            comm['uid'] = None

        if comm['status']:
            comm['content'] = ''
            comm['lastedit'] = None
        del comm['userstatus']
        commdata[comm['cid']] = comm


    def recursive_populate(tree):
        """ Expands the tree with the data from `commdata` """
        populated_tree = []
        for i in tree:
            if not i['cid']:
                populated_tree.append(i)
                continue
            comment = commdata[i['cid']]
            comment['content'] = misc.our_markdown(comment['content'])
            comment['children'] = recursive_populate(i['children'])
            populated_tree.append(comment)
        return populated_tree

    comment_tree = recursive_populate(comment_tree)
    return comment_tree


@API.route('/getPost/<int:pid>/comments', methods=['get'])
@jwt_optional
def get_post_comments(pid):
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

    comment_tree = get_comment_tree(comments, uid=current_user)
    return jsonify(comments=comment_tree)


@API.route('/getPost/<int:pid>/comments/children/<cid>/<lim>', methods=['get'])
@API.route('/getPost/<int:pid>/comments/children/<cid>', methods=['get'], defaults={'lim': ''})
def get_post_comment_children(pid, cid, lim):
    """ if lim is not present, load all children for cid.
    if lim is present, load all comments after (???) index lim

    NOTE: This is a crappy solution since comment sorting might change when user is
    seeing the page and we might end up re-sending a comment (will show as duplicate).
    This can be solved by the front-end checking if a cid was already rendered, but it
    is a horrible solution
    """
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
        comment_tree = get_comment_tree(comments, cid, lim)
    elif cid != '0':
        comment_tree = get_comment_tree(comments, cid)
    else:
        return jsonify(msg='Illegal comment id'), 400
    return jsonify(comments=comment_tree)


@API.route('/getPostList/<target>/<sort>', defaults={'page': 1}, methods=['GET'])
@API.route('/getPostList/<target>/<sort>/<int:page>', methods=['GET'])
@jwt_optional
def get_post_list(target, sort, page):
    """ Same as v2, but `content` is returned as parsed markdown and the `sort` can be `default`
    when `target` is a sub """
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
            sub = Sub.get(Sub.name == target)
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

    posts = misc.getPostList(base_query, sort, page).dicts()

    cnt = base_query.count() - page * 25
    postlist = []
    for post in posts:
        if post['userstatus'] == 10:  # account deleted
            post['user'] = '[Deleted]'
            post['uid'] = None
        del post['userstatus']
        post['content'] = misc.our_markdown(post['content']) if post['ptype'] != 1 else ''
        postlist.append(post)

    return jsonify(posts=postlist, sort=sort, continues=True if cnt > 0 else False)


@API.route('/vote/<target_type>/<pcid>/<value>', methods=['POST'])
@jwt_required
def vote_post(target_type, pcid, value):
    """ Logs an upvote to a post. """
    uid = get_jwt_identity()
    try:
        user = User.get(User.uid == uid)
    except User.DoesNotExist:
        return jsonify(msg="Unknown error. User disappeared"), 403

    if value == "up":
        voteValue = 1
    elif value == "down":
        voteValue = -1
        if user.given < 0:
            return jsonify(msg='Score balance is negative'), 403
    else:
        return jsonify(msg="Invalid vote value"), 400

    if target_type == "post":
        target_model = SubPost
        try:
            target = SubPost.select(SubPost.uid, SubPost.score, SubPost.upvotes, SubPost.downvotes, SubPost.pid.alias('id'), SubPost.posted)
            target = target.where(SubPost.pid == pcid).get()
        except SubPost.DoesNotExist:
            return jsonify(msg='Post does not exist'), 404

        if target.deleted:
            return jsonify(msg="You can't vote on deleted posts"), 400

        try:
            qvote = SubPostVote.select().where(SubPostVote.pid == pcid).where(SubPostVote.uid == uid).get()
        except SubPostVote.DoesNotExist:
            qvote = False
    elif target_type == "comment":
        target_model = SubPostComment
        try:
            target = SubPostComment.select(SubPostComment.uid, SubPost.sid, SubPostComment.pid, SubPostComment.status, SubPostComment.score,
                                           SubPostComment.upvotes, SubPostComment.downvotes, SubPostComment.cid.alias('id'), SubPostComment.time.alias('posted'))
            target = target.join(SubPost).where(SubPostComment.cid == pcid).objects().get()
        except SubPostComment.DoesNotExist:
            return jsonify(msg='Comment does not exist'), 404

        if target.status:
            return jsonify(msg="You can't vote on deleted comments"), 400

        try:
            qvote = SubPostCommentVote.select().where(SubPostCommentVote.cid == pcid).where(SubPostCommentVote.uid == uid).get()
        except SubPostCommentVote.DoesNotExist:
            qvote = False
    else:
        return jsonify(msg="Invalid target"), 400

    try:
        SubMetadata.get((SubMetadata.sid == target.sid) & (SubMetadata.key == "ban") & (SubMetadata.value == user.uid))
        return jsonify(msg='You are banned on this sub.'), 403
    except SubMetadata.DoesNotExist:
        pass

    if (datetime.datetime.utcnow() - target.posted) > datetime.timedelta(days=60):
        return jsonify(msg="Post is archived"), 400

    user = User.get(User.uid == target.uid)

    positive = True if voteValue == 1 else False
    undone = False
    if qvote:
        if bool(qvote.positive) == (True if voteValue == 1 else False):
            qvote.delete_instance()

            if positive:
                upd_q = target_model.update(score=target_model.score - voteValue, upvotes=target_model.upvotes - 1)
            else:
                upd_q = target_model.update(score=target_model.score - voteValue, downvotes=target_model.downvotes - 1)
            new_score = -voteValue
            undone = True
            User.update(score=User.score - voteValue).where(User.uid == target.uid).execute()
            User.update(given=User.given - voteValue).where(User.uid == uid).execute()
        else:
            qvote.positive = positive
            qvote.save()

            if positive:
                upd_q = target_model.update(score=target_model.score + (voteValue * 2), upvotes=target_model.upvotes + 1, downvotes=target_model.downvotes - 1)
            else:
                upd_q = target_model.update(score=target_model.score + (voteValue * 2), upvotes=target_model.upvotes - 1, downvotes=target_model.downvotes + 1)
            new_score = (voteValue * 2)
            User.update(score=User.score + (voteValue * 2)).where(User.uid == target.uid).execute()
            User.update(given=User.given + voteValue).where(User.uid == uid).execute()
    else: # First vote cast on post
        now = datetime.datetime.utcnow()
        if target_type == "post":
            sp_vote = SubPostVote.create(pid=pcid, uid=uid, positive=positive, datetime=now)
        else:
            sp_vote = SubPostCommentVote.create(cid=pcid, uid=uid, positive=positive, datetime=now)

        sp_vote.save()

        if positive:
            upd_q = target_model.update(score=target_model.score + voteValue, upvotes=target_model.upvotes + 1)
        else:
            upd_q = target_model.update(score=target_model.score + voteValue, downvotes=target_model.downvotes + 1)
        new_score = voteValue
        User.update(score=User.score + voteValue).where(User.uid == target.uid).execute()
        User.update(given=User.given + voteValue).where(User.uid == uid).execute()

    if target_type == "post":
        upd_q.where(SubPost.pid == target.id).execute()
        socketio.emit('threadscore', {'pid': target.pid, 'score': target.score + new_score},
                      namespace='/snt', room=target.pid)

        socketio.emit('yourvote', {'pid': target.pid, 'status': 0, 'score': target.score + new_score}, namespace='/snt',
                      room='user' + uid)
    else:
        upd_q.where(SubPostComment.cid == target.id).execute()

    socketio.emit('uscore', {'score': target.score + new_score},
                  namespace='/snt', room="user" + target.uid_id)

    return jsonify(score=target.score + new_score, rm=undone)


@API.route('/create/comment', methods=['POST'])
@jwt_required
@misc.ratelimit(1, per=30, over_limit=api_over_limit)  # Once every 30 secs
def create_comment():
    uid = get_jwt_identity()
    if not request.is_json:
        return jsonify(msg="Missing JSON in request"), 400

    pid = request.json.get('pid', None)
    parentcid = request.json.get('parentcid', None)
    content = request.json.get('content', None)

    if not pid or not content:
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

    if (datetime.datetime.utcnow() - post.posted) > datetime.timedelta(days=60):
        return jsonify(msg="Post is archived"), 403

    try:
        SubMetadata.get((SubMetadata.sid == post.sid) & (SubMetadata.key == "ban") & (SubMetadata.value == user.uid))
        return jsonify(msg='You are banned on this sub.'), 403
    except SubMetadata.DoesNotExist:
        pass

    if parentcid:
        try:
            parent = SubPostComment.get(SubPostComment.cid == parentcid)
        except SubPostComment.DoesNotExist:
            return jsonify(msg="Parent comment does not exist"), 404

        if parent.status is not None or parent.pid.pid != post.pid:
            return jsonify(msg="Parent comment does not exist"), 404

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
        subject = 'Comment reply: ' + post.title
        mtype = 5
    else:
        notif_to = post.uid_id
        subject = 'Post reply: ' + post.title
        mtype = 4
    if notif_to != uid and uid not in misc.get_ignores(notif_to):
        misc.create_message(mfrom=uid,
                            to=notif_to,
                            subject=subject,
                            content='',
                            link=comment.cid,
                            mtype=mtype)
        socketio.emit('notification', {'count': misc.get_notification_count(notif_to)},
                      namespace='/snt', room='user' + notif_to)

    # 6 - Process mentions
    sub = Sub.get_by_id(post.sid)
    misc.workWithMentions(content, notif_to, post, sub, cid=comment.cid)

    return jsonify(pid=pid, cid=comment.cid), 200

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
    challenge_token = request.json.get('challenge_token')
    challenge_response = request.json.get('challenge_response')

    if not challenge_token or not challenge_response:
        raise ChallengeRequired

    if not misc.validate_captcha(challenge_token, challenge_response):
        raise ChallengeWrong

    return True


@API.route('/challenge', methods=['GET'])
@jwt_required
def get_challenge():
    challenge = misc.create_captcha()
    return jsonify(challenge_token=challenge[0], challenge_blob=challenge[1])


@API.route('/create/post', methods=['POST'])
@jwt_required
@misc.ratelimit(1, per=30, over_limit=api_over_limit)  # Once every 30 secs
def create_post():
    uid = get_jwt_identity()
    if not request.is_json:
        return jsonify(msg="Missing JSON in request"), 400

    sub = request.json.get('sub', None)
    ptype = request.json.get('ptype', None)
    title = request.json.get('title', None)
    link = request.json.get('link', None)
    content = request.json.get('content', None)
    nsfw = request.json.get('nsfw', False)

    if not sub or ptype is None or not title:
        return jsonify(msg='Missing required parameters'), 400

    if ptype not in (0, 1, 3):
        return jsonify(msg='Illegal value for ptype'), 400

    if ptype == 3:
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
        sub = Sub.get(Sub.name == sub)
    except Sub.DoesNotExist:
        return jsonify(msg="Sub does not exist"), 404

    if sub in ('all', 'new', 'hot', 'top', 'admin', 'home'):  # TODO: Make this a blacklist setting in the config file?
        return jsonify(msg="You can't post on this sub"), 403

    subdata = misc.getSubData(sub.sid, simple=True)

    if uid in subdata.get('ban', []):
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

    if ptype == 1:
        if not 'link':
            return jsonify(msg='No link provided'), 400

        if content:
            return jsonify(msg='Link posts do not accept content'), 400

        if misc.is_domain_banned(link):
            return jsonify(msg="Link's domain is banned"), 400

        recent = datetime.datetime.utcnow() - datetime.timedelta(days=5)
        try:
            wpost = SubPost.select().where(SubPost.sid == sub.sid).where(SubPost.link == link)
            wpost = wpost.where(SubPost.deleted == 0).where(SubPost.posted > recent).get()
            return jsonify(msg="This link has already been posted recently on this sub"), 403
        except SubPost.DoesNotExist:
            pass
    elif ptype == 0:
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
                          link=link if ptype == 1 else None,
                          posted=datetime.datetime.utcnow(),
                          score=1, upvotes=1, downvotes=0, deleted=0, comments=0,
                          ptype=ptype,
                          nsfw=nsfw if not subdata.get('nsfw') == '1' else 1,
                          thumbnail=misc.get_thumbnail(link) if ptype == 1 else '')

    Sub.update(posts=Sub.posts + 1).where(Sub.sid == sub.sid).execute()
    addr = url_for('sub.view_post', sub=sub.name, pid=post.pid)
    posts = misc.getPostList(misc.postListQueryBase(nofilter=True).where(SubPost.pid == post.pid), 'new', 1).dicts()
    socketio.emit('thread',
                  {'addr': addr, 'sub': sub.name, 'type': ptype,
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
