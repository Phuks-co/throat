""" API endpoints. """

import datetime
import bcrypt
from flask import Blueprint, jsonify, request
from peewee import JOIN
from flask_jwt_extended import JWTManager, jwt_required, create_access_token, create_refresh_token, get_jwt_identity
from flask_jwt_extended import jwt_refresh_token_required, jwt_optional
from .. import misc
from ..socketio import socketio
from ..models import Sub, User, SubPost, SubPostComment, SubMetadata, SubPostCommentVote, SubPostVote, SubSubscriber
from ..models import SiteMetadata

API = Blueprint('apiv3', __name__)

JWT = JWTManager()


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
    return jsonify(status='ok', access_token=access_token, refresh_token=refresh_token), 200


@API.route('/refresh', methods=['POST'])
@jwt_refresh_token_required
def refresh():
    """ Returns a new access token. Requires providing a refresh token """
    current_user = get_jwt_identity()
    new_token = create_access_token(identity=current_user, fresh=False)
    return jsonify(status='ok', access_token=new_token), 200


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
    return jsonify(status='ok', access_token=new_token)


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
            comment_tree = [comment_tree]
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
        return jsonify(status='error', error="Post does not exist")

    # 1 - Fetch all comments (only cid and parentcid)
    comments = SubPostComment.select(SubPostComment.cid, SubPostComment.parentcid).where(SubPostComment.pid == post.pid).order_by(SubPostComment.score.desc()).dicts()
    if not comments.count():
        return jsonify(status='ok', comments=[])

    comment_tree = get_comment_tree(comments, uid=current_user)
    return jsonify(status='ok', comments=comment_tree)


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
        return jsonify(status='error', error='Post does not exist')
    if cid == 'null':
        cid = '0'
    if cid != '0':
        try:
            root = SubPostComment.get(SubPostComment.cid == cid)
            if root.pid_id != post.pid:
                return jsonify(status='error', error='Comment does not belong to the given post')
        except SubPostComment.DoesNotExist:
            return jsonify(status='error', error='Post does not exist')

    comments = SubPostComment.select(SubPostComment.cid, SubPostComment.parentcid).where(SubPostComment.pid == pid).order_by(SubPostComment.score.desc()).dicts()
    if not comments.count():
        return jsonify(status='ok', comments=[])

    if lim:
        if cid == '0':
            cid = None
        comment_tree = get_comment_tree(comments, cid, lim)
    elif cid != '0':
        comment_tree = get_comment_tree(comments, cid)
    else:
        return jsonify(status='error', error='Illegal comment id')
    return jsonify(status='ok', comments=comment_tree)


@API.route('/getPostList/<target>/<sort>', defaults={'page': 1}, methods=['GET'])
@API.route('/getPostList/<target>/<sort>/<int:page>', methods=['GET'])
@jwt_optional
def get_post_list(target, sort, page):
    """ Same as v2, but `content` is returned as parsed markdown and the `sort` can be `default`
    when `target` is a sub """
    if sort not in ('hot', 'top', 'new', 'default'):
        return jsonify(status="error", error="Invalid sort")
    if page < 1:
        return jsonify(status="error", error="Invalid page number")

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
            return jsonify(status="error", error="Invalid sort")
        if uid:
            base_query = base_query.where(SubPost.sid.not_in(blocked))
    elif target == 'home':
        if sort == 'default':
            return jsonify(status="error", error="Invalid sort")

        if not uid:
            base_query = base_query.join(SiteMetadata, JOIN.LEFT_OUTER, on=(SiteMetadata.key == 'default')).where(SubPost.sid == SiteMetadata.value)
        else:
            base_query = base_query.where(SubPost.sid << subscribed)
            base_query = base_query.where(SubPost.sid.not_in(blocked))

    else:
        try:
            sub = Sub.get(Sub.name == target)
        except Sub.DoesNotExist:
            return jsonify(status="error", error="Target does not exist")

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

    return jsonify(status='ok', posts=postlist, sort=sort, continues=True if cnt > 0 else False)


@API.route('/vote/post/<pid>/<value>', methods=['POST'])
@jwt_required
def upvote(pid, value):
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

    try:
        post = SubPost.get(SubPost.pid == pid)
    except SubPost.DoesNotExist:
        return jsonify(msg='Post does not exist'), 404

    if post.deleted:
        return jsonify(msg="You can't vote on deleted posts"), 400

    try:
        SubMetadata.get((SubMetadata.sid == post.sid) & (SubMetadata.key == "ban") & (SubMetadata.value == user.uid))
        return jsonify(msg='You are banned on this sub.'), 403
    except SubMetadata.DoesNotExist:
        pass

    if (datetime.datetime.utcnow() - post.posted) > datetime.timedelta(days=60):
        return jsonify(msg="Post is archived"), 400
    try:
        qvote = SubPostVote.select().where(SubPostVote.pid == pid).where(SubPostVote.uid == uid).get()
    except SubPostVote.DoesNotExist:
        qvote = False
    user = User.get(User.uid == post.uid)

    positive = True if voteValue == 1 else False
    if qvote:
        if bool(qvote.positive) == (True if voteValue == 1 else False):
            qvote.delete_instance()

            if positive:
                SubPost.update(score=SubPost.score - voteValue, upvotes=SubPost.upvotes - 1).where(SubPost.pid == post.pid).execute()
            else:
                SubPost.update(score=SubPost.score - voteValue, downvotes=SubPost.downvotes - 1).where(SubPost.pid == post.pid).execute()

            User.update(score=User.score - voteValue).where(User.uid == post.uid).execute()
            User.update(given=User.given - voteValue).where(User.uid == uid).execute()
            socketio.emit('uscore',
                          {'score': user.score - voteValue},
                          namespace='/snt', room="user" + post.uid.uid)

            socketio.emit('threadscore',
                          {'pid': post.pid, 'score': post.score - voteValue},
                          namespace='/snt', room=post.pid)

            socketio.emit('yourvote', {'pid': post.pid, 'status': 0, 'score': post.score - voteValue}, namespace='/snt',
                          room='user' + uid)
            

            return jsonify(status='ok', message='Vote removed', score=post.score - voteValue, rm=True)
        else:
            qvote.positive = positive
            qvote.save()

            if positive:
                SubPost.update(score=SubPost.score + (voteValue * 2), upvotes=SubPost.upvotes + 1, downvotes=SubPost.downvotes - 1).where(SubPost.pid == post.pid).execute()
            else:
                SubPost.update(score=SubPost.score + (voteValue * 2), upvotes=SubPost.upvotes - 1, downvotes=SubPost.downvotes + 1).where(SubPost.pid == post.pid).execute()

            User.update(score=User.score + (voteValue * 2)).where(User.uid == post.uid).execute()
            User.update(given=User.given + voteValue).where(User.uid == uid).execute()

            socketio.emit('uscore',
                            {'score': user.score + voteValue * 2},
                            namespace='/snt',
                            room="user" + post.uid.uid)

            socketio.emit('threadscore',
                          {'pid': post.pid,
                           'score': post.score + voteValue * 2},
                          namespace='/snt',
                          room=post.pid)
            
            socketio.emit('yourvote', {'pid': post.pid, 'status': voteValue, 'score': post.score + voteValue * 2}, namespace='/snt',
                          room='user' + uid)
            return jsonify(status='ok', message='Vote flipped', score=post.score + voteValue * 2)
    else: # First vote cast on post
        now = datetime.datetime.utcnow()
        sp_vote = SubPostVote.create(pid=pid, uid=uid, positive=positive, datetime=now)
        sp_vote.save()

        if positive:
            SubPost.update(score=SubPost.score + voteValue, upvotes=SubPost.upvotes + 1).where(SubPost.pid == post.pid).execute()
        else:
            SubPost.update(score=SubPost.score + voteValue, downvotes=SubPost.downvotes + 1).where(SubPost.pid == post.pid).execute()

        socketio.emit('threadscore', {'pid': post.pid, 'score': post.score + voteValue},
                      namespace='/snt', room=post.pid)
        socketio.emit('yourvote', {'pid': post.pid, 'status': voteValue, 'score': post.score + voteValue},
                      namespace='/snt', room='user' + uid)

        User.update(score=User.score + voteValue).where(User.uid == post.uid).execute()
        User.update(given=User.given + voteValue).where(User.uid == uid).execute()

        socketio.emit('uscore', {'score': user.score + voteValue},
                      namespace='/snt', room="user" + post.uid.uid)
        
        return jsonify(status='ok', score=post.score + voteValue)