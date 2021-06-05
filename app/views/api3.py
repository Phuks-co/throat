""" API endpoints. """

import datetime
import uuid
from bs4 import BeautifulSoup
from email_validator import EmailNotValidError
from flask import Blueprint, jsonify, request, url_for
from peewee import JOIN, fn
from flask_jwt_extended import (
    JWTManager,
    jwt_required,
    create_access_token,
    create_refresh_token,
    get_jwt_identity,
)
from flask_jwt_extended import jwt_refresh_token_required, jwt_optional
from .. import misc
from .. import tasks
from ..auth import (
    auth_provider,
    email_validation_is_required,
    create_user,
    normalize_email,
)
from ..socketio import socketio
from ..misc import ratelimit, POSTING_LIMIT, AUTH_LIMIT
from ..models import (
    Sub,
    User,
    SubPost,
    SubPostComment,
    SubMetadata,
    SubPostCommentVote,
    SubPostVote,
    SubSubscriber,
)
from ..models import (
    SiteMetadata,
    UserMetadata,
    Message,
    MessageType,
    MessageMailbox,
    UserUnreadMessage,
    UserMessageMailbox,
    SubRule,
    Notification,
    SubMod,
    InviteCode,
    UserStatus,
)
from ..models import SubPostMetadata, UserIgnores
from ..caching import cache
from ..config import config
from ..badges import badges
from ..notifications import notifications

API = Blueprint("apiv3", __name__)

JWT = JWTManager()


@API.errorhandler(429)
def ratelimit_handler(_):
    return jsonify(msg="Rate limited. Please try again later"), 429


@API.route("/login", methods=["POST"])
@ratelimit(AUTH_LIMIT)
def login():
    """Logs the user in.
    Parameters (json): username and password
    Returns: access token and refresh token
    """
    if not request.is_json:
        return jsonify(msg="Missing JSON in request"), 400

    username = request.json.get("username", None)
    password = request.json.get("password", None)
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

    if not auth_provider.validate_password(user, password):
        return jsonify(msg="Bad username or password"), 401

    # Identity can be any data that is json serializable
    access_token = create_access_token(identity=user.uid, fresh=True)
    refresh_token = create_refresh_token(identity=user.uid)
    return (
        jsonify(
            access_token=access_token, refresh_token=refresh_token, username=user.name
        ),
        200,
    )


@API.route("/register", methods=["GET"])
def register_params():
    return {
        "enabled": config.site.enable_registration,
        "mandatory": {
            "email": email_validation_is_required(),
            "invite_code": config.site.require_invite_code,
        },
    }


@API.route("/register", methods=["POST"])
@ratelimit(AUTH_LIMIT)
def register():
    """Creates a new account.
    Params (json):
        - username
        - password
        - email (may be optional)
        - invite_code (may be optional)

    Check GET /register to see if email and invite codes are mandatory.
    Returns:
        - HTTP code 423: Challenge required (captcha or other)
        - HTTP 403: Registration disabled
        - HTTP 200: User successfully registered. Check the `status` field, if status == 1 then e-mail validation is
        required
    """
    if not request.is_json:
        return jsonify(msg="Missing JSON in request"), 400
    username = request.json.get("username", None)
    password = request.json.get("password", None)
    email = request.json.get("email", None)
    invite_code = request.json.get("inviteCode", None)
    check_challenge()

    if not username or not password:
        return jsonify(msg="Missing mandatory parameters"), 403

    if len(password) < 6:
        return jsonify(msg="Password too short"), 403

    if not config.site.enable_registration:
        return jsonify(msg="Registration disabled"), 403

    if email_validation_is_required() and email is None:
        return jsonify(msg="E-mail is mandatory"), 401

    if not misc.allowedNames.match(username):
        return jsonify(msg="Invalid username"), 401
    if email:
        try:
            email = normalize_email(email)
        except EmailNotValidError:
            return jsonify(msg="Invalid email"), 401
        if misc.is_domain_banned(email, domain_type="email"):
            return jsonify(msg="Email not allowed"), 401

    existing_user = None
    try:
        existing_user = User.get(fn.Lower(User.name) == username.lower())
        jointime = datetime.datetime.utcnow() - existing_user.joindate
        if existing_user.status != UserStatus.PROBATION or jointime.days < 2:
            return jsonify(msg="Username already in use"), 401
    except User.DoesNotExist:
        pass

    if len(password) < 7:
        return jsonify(msg="Password too short"), 401

    if len(username) < 2:
        return jsonify(msg="Username too short"), 401

    if config.site.require_invite_code:
        if invite_code is None:
            return jsonify(msg="E-mail is mandatory"), 401
        try:
            InviteCode.get_valid(invite_code)
        except InviteCode.DoesNotExist:
            return jsonify(msg="Invalid invite code"), 401

        InviteCode.update(uses=InviteCode.uses + 1).where(
            InviteCode.code == invite_code
        ).execute()

    user = create_user(username, password, email, invite_code, existing_user)
    return {
        "status": user.status,
        "username": user.name,
        "email": user.email,
    }


@API.route("/refresh", methods=["POST"])
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


@API.route("/fresh-login", methods=["POST"])
@ratelimit(AUTH_LIMIT)
def fresh_login():
    """ Returns a fresh access token. Requires username and password """
    if not request.is_json:
        return jsonify(msg="Missing JSON in request"), 400
    username = request.json.get("username", None)
    password = request.json.get("password", None)
    try:
        user = User.get(fn.Lower(User.name) == username.lower())
    except User.DoesNotExist:
        return jsonify(msg="Bad username or password"), 401

    if not auth_provider.validate_password(user, password):
        return jsonify(msg="Bad username or password"), 401

    new_token = create_access_token(identity=user.uid, fresh=True)
    return jsonify(access_token=new_token)


@API.route("/post/<target>", methods=["GET"])
@jwt_optional
def get_post_list(target):
    """Same as v2, but `content` is returned as parsed markdown and the `sort` can be `default`
    when `target` is a sub"""

    if target not in ("all", "home"):
        sort = request.args.get("sort", default="default")
    else:
        sort = request.args.get("sort", default="new")
    page = request.args.get("page", default=1, type=int)

    if sort not in ("hot", "top", "new", "default"):
        return jsonify(msg="Invalid sort"), 400
    if page < 1:
        return jsonify(msg="Invalid page number"), 400

    uid = get_jwt_identity()
    base_query = SubPost.select(
        SubPost.nsfw,
        SubPost.content,
        SubPost.pid,
        SubPost.title,
        SubPost.posted,
        SubPost.score,
        SubPost.thumbnail,
        SubPost.link,
        User.name.alias("user"),
        Sub.name.alias("sub"),
        SubPost.flair,
        SubPost.edited,
        SubPost.comments,
        SubPost.ptype,
        User.status.alias("userstatus"),
        User.uid,
        SubPost.upvotes,
        *([SubPost.downvotes, SubPostVote.positive] if uid else [SubPost.downvotes]),
    )
    blocked = []
    subscribed = []
    if uid:
        base_query = base_query.join(
            SubPostVote,
            JOIN.LEFT_OUTER,
            on=((SubPostVote.pid == SubPost.pid) & (SubPostVote.uid == uid)),
        ).switch(SubPost)
        subs = SubSubscriber.select().where(SubSubscriber.uid == uid)
        subs = subs.order_by(SubSubscriber.order.asc())
        subscribed = [x.sid_id for x in subs if x.status == 1]
        blocked = [x.sid_id for x in subs if x.status == 2]

    base_query = (
        base_query.join(User, JOIN.LEFT_OUTER)
        .switch(SubPost)
        .join(Sub, JOIN.LEFT_OUTER)
    )

    if target == "all":
        if sort == "default":
            return jsonify(msg="Invalid sort"), 400
        if uid:
            base_query = base_query.where(SubPost.sid.not_in(blocked))
    elif target == "home":
        if sort == "default":
            return jsonify(msg="Invalid sort"), 400

        if not uid:
            base_query = base_query.join(
                SiteMetadata, JOIN.LEFT_OUTER, on=(SiteMetadata.key == "default")
            ).where(SubPost.sid == SiteMetadata.value)
        else:
            base_query = base_query.where(SubPost.sid << subscribed)
            base_query = base_query.where(SubPost.sid.not_in(blocked))

    else:
        try:
            sub = Sub.get(fn.Lower(Sub.name) == target.lower())
        except Sub.DoesNotExist:
            return jsonify(msg="Target does not exist"), 404

        if sort == "default":
            try:
                sort = SubMetadata.get(
                    (SubMetadata.sid == sub.sid) & (SubMetadata.key == "sort")
                )
                sort = sort.value
            except SubMetadata.DoesNotExist:
                sort = "hot"

            if sort == "v":
                sort = "hot"
            elif sort == "v_two":
                sort = "new"
            elif sort == "v_three":
                sort = "top"
        base_query = base_query.where(Sub.sid == sub.sid)

    base_query = base_query.where(SubPost.deleted == 0)
    posts = misc.getPostList(base_query, sort, page).dicts()

    cnt = base_query.count() - page * 25
    postList = []
    for post in posts:
        if post["userstatus"] == 10:  # account deleted
            post["user"] = "[Deleted]"
        post["archived"] = (
            datetime.datetime.utcnow() - post["posted"].replace(tzinfo=None)
        ) > datetime.timedelta(days=config.site.archive_post_after)
        del post["userstatus"]
        del post["uid"]
        post["content"] = (
            misc.our_markdown(post["content"]) if post["ptype"] != 1 else ""
        )
        postList.append(post)

    return jsonify(posts=postList, sort=sort, continues=True if cnt > 0 else False)


@API.route("/post/<sub>/<int:pid>", methods=["GET"])
@jwt_optional
def get_post(sub, pid):
    """Returns information for a post """
    uid = get_jwt_identity()
    base_query = SubPost.select(
        SubPost.nsfw,
        SubPost.content,
        SubPost.pid,
        SubPost.title,
        SubPost.posted,
        SubPost.score,
        SubPost.deleted,
        SubPost.thumbnail,
        SubPost.link,
        User.name.alias("user"),
        Sub.name.alias("sub"),
        SubPost.flair,
        SubPost.edited,
        SubPost.comments,
        SubPost.ptype,
        User.status.alias("userstatus"),
        User.uid,
        SubPost.upvotes,
        *([SubPost.downvotes, SubPostVote.positive] if uid else [SubPost.downvotes]),
    )

    if uid:
        base_query = base_query.join(
            SubPostVote,
            JOIN.LEFT_OUTER,
            on=((SubPostVote.pid == SubPost.pid) & (SubPostVote.uid == uid)),
        ).switch(SubPost)
    base_query = (
        base_query.join(User, JOIN.LEFT_OUTER)
        .switch(SubPost)
        .join(Sub, JOIN.LEFT_OUTER)
    )

    post = base_query.where(
        (SubPost.pid == pid) & (fn.Lower(Sub.name) == sub.lower())
    ).dicts()

    if not post.count():
        return jsonify(msg="Post does not exist"), 404

    post = post[0]
    post["deleted"] = True if post["deleted"] != 0 else False

    if post["deleted"]:  # Clear data for deleted posts
        post["content"] = None
        post["link"] = None
        post["uid"] = None
        post["user"] = "[Deleted]"
        post["thumbnail"] = None
        post["edited"] = None

    post["source"] = post["content"]
    if post["content"]:
        post["content"] = misc.our_markdown(post["content"])

    if post["userstatus"] == 10:
        post["user"] = "[Deleted]"

    post["archived"] = (
        datetime.datetime.utcnow() - post["posted"].replace(tzinfo=None)
    ) > datetime.timedelta(days=config.site.archive_post_after)
    if post["ptype"] == 0:
        post["type"] = "text"
    elif post["ptype"] == 1:
        post["type"] = "link"
    elif post["ptype"] == 2:
        post["type"] = "upload"
    elif post["ptype"] == 3:
        post["type"] = "poll"
    del post["ptype"]
    del post["userstatus"]
    del post["uid"]

    return jsonify(post=post)


@API.route("/post/<sub>/<int:pid>", methods=["PATCH"])
@jwt_required
def edit_post(sub, pid):
    uid = get_jwt_identity()
    if not request.is_json:
        return jsonify(msg="Missing JSON in request"), 400
    content = request.json.get("content", None)
    if not content:
        return jsonify(msg="Content parameter required"), 400

    if len(content) > 16384:
        return jsonify(msg="Content is too long"), 400

    try:
        post = (
            SubPost.select()
            .join(Sub, JOIN.LEFT_OUTER)
            .where((SubPost.pid == pid) & (fn.Lower(Sub.name) == sub.lower()))
        )
        post = post.where(SubPost.deleted == 0).get()
    except SubPost.DoesNotExist:
        return jsonify(msg="Post does not exist"), 404

    if post.uid_id != uid:
        return jsonify(msg="Unauthorized"), 403

    if misc.is_sub_banned(sub, uid=uid):
        return jsonify(msg="You are banned on this sub."), 403

    if post.is_archived():
        return jsonify(msg="Post is archived"), 403

    post.content = content
    # Only save edited time if it was posted more than five minutes ago
    if (datetime.datetime.utcnow() - post.posted.replace(tzinfo=None)).seconds > 300:
        post.edited = datetime.datetime.utcnow()
    post.save()
    return get_post(sub, pid)


@API.route("/post/<sub>/<int:pid>", methods=["DELETE"])
@jwt_required
def delete_post(sub, pid):
    uid = get_jwt_identity()
    try:
        post = (
            SubPost.select()
            .join(Sub, JOIN.LEFT_OUTER)
            .where((SubPost.pid == pid) & (fn.Lower(Sub.name) == sub.lower()))
        )
        post = post.where(SubPost.deleted == 0).get()
    except SubPost.DoesNotExist:
        return jsonify(msg="Post does not exist"), 404

    # TODO: Implement admin logic in the api
    if not misc.is_sub_mod(uid, post.sid_id, 2) and post.uid_id != uid:
        return jsonify(msg="Unauthorized"), 403

    if post.uid_id == uid:
        post.deleted = 1
    else:
        reason = request.args.get("reason", default=None)
        if not reason:
            return jsonify(msg="Cannot delete post without reason"), 400
        post.deleted = 2
        # TODO: Make this a translatable notification
        Notification.create(
            type="POST_DELETE",
            sub=post.sid,
            post=post.pid,
            content="Dôvod: " + reason,
            sender=uid,
            target=post.uid,
        )

        misc.create_sublog(
            misc.LOG_TYPE_SUB_DELETE_POST,
            uid,
            post.sid,
            comment=reason,
            link=url_for("site.view_post_inbox", pid=post.pid),
            admin=False,
        )

    if (datetime.datetime.utcnow() - post.posted.replace(tzinfo=None)).seconds < 86400:
        socketio.emit("deletion", {"pid": post.pid}, namespace="/snt", room="/all/new")

    # check if the post is an announcement. Unannounce if it is.
    try:
        ann = (
            SiteMetadata.select()
            .where(SiteMetadata.key == "announcement")
            .where(SiteMetadata.value == post.pid)
            .get()
        )
        ann.delete_instance()
        cache.delete_memoized(misc.getAnnouncementPid)
    except SiteMetadata.DoesNotExist:
        pass
    post.save()
    Sub.update(posts=Sub.posts - 1).where(Sub.sid == post.sid).execute()
    return jsonify(), 200


@API.route("/post/<_sub>/<int:pid>/vote", methods=["POST"])
@jwt_required
def vote_post(_sub, pid):
    """ Logs an upvote to a post. """
    uid = get_jwt_identity()
    if not request.is_json:
        return jsonify(msg="Missing JSON in request"), 400
    value = request.json.get("upvote", None)
    if type(value) is not bool:
        return jsonify(msg="Upvote must be true or false")

    return misc.cast_vote(uid, "post", pid, value)


@API.route("/post/<_sub>/<int:pid>/comment", methods=["GET"])
@jwt_optional
def get_post_comments(_sub, pid):
    """Returns comment tree

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
    comments = (
        SubPostComment.select(SubPostComment.cid, SubPostComment.parentcid)
        .where(SubPostComment.pid == post.pid)
        .order_by(SubPostComment.score.desc())
        .dicts()
    )
    if not comments.count():
        return jsonify(comments=[])

    comment_tree = misc.get_comment_tree(
        post.pid, post.sid.get_id(), comments, uid=current_user
    )
    return jsonify(comments=comment_tree)


@API.route("/post/<sub>/<int:pid>/comment", methods=["POST"])
@jwt_required
@ratelimit(POSTING_LIMIT)
def create_comment(sub, pid):
    uid = get_jwt_identity()
    if not request.is_json:
        return jsonify(msg="Missing JSON in request"), 400

    parentcid = request.json.get("parentcid", None)
    content = request.json.get("content", None)

    if not content:
        return jsonify(msg="Missing required parameters"), 400

    try:
        user = User.get(User.uid == uid)
    except User.DoesNotExist:
        return jsonify(msg="Unknown error. User disappeared"), 403

    try:
        post = SubPost.get(SubPost.pid == pid)
    except SubPost.DoesNotExist:
        return jsonify(msg="Post does not exist"), 404
    if post.deleted:
        return jsonify(msg="Post was deleted"), 404

    if post.is_archived():
        return jsonify(msg="Post is archived"), 403

    postmeta = misc.metadata_to_dict(
        SubPostMetadata.select().where(SubPostMetadata.pid == pid)
    )
    if postmeta.get("lock-comments"):
        return jsonify(msg="Comments are closed on this post."), 403

    try:
        SubMetadata.get(
            (SubMetadata.sid == post.sid)
            & (SubMetadata.key == "ban")
            & (SubMetadata.value == user.uid)
        )
        return jsonify(msg="You are banned on this sub."), 403
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

    comment = SubPostComment.create(
        pid=pid,
        uid=uid,
        content=content,
        parentcid=parentcid,
        time=datetime.datetime.utcnow(),
        cid=uuid.uuid4(),
        score=0,
        upvotes=0,
        downvotes=0,
    )

    SubPost.update(comments=SubPost.comments + 1).where(
        SubPost.pid == post.pid
    ).execute()

    socketio.emit(
        "threadcomments",
        {"pid": post.pid, "comments": post.comments + 1},
        namespace="/snt",
        room=post.pid,
    )

    defaults = [
        x.value for x in SiteMetadata.select().where(SiteMetadata.key == "default")
    ]
    comment_res = misc.word_truncate(
        "".join(
            BeautifulSoup(misc.our_markdown(comment.content), features="lxml").findAll(
                text=True
            )
        ).replace("\n", " "),
        250,
    )
    sub = Sub.get(Sub.name == sub)
    socketio.emit(
        "comment",
        {
            "sub": sub.name,
            "show_sidebar": (
                sub.sid in defaults or config.site.recent_activity.defaults_only
            ),
            "user": user.name,
            "pid": post.pid,
            "sid": sub.sid,
            "content": comment_res,
            "post_url": url_for("sub.view_post", sub=sub.name, pid=post.pid),
            "sub_url": url_for("sub.view_sub", sub=sub.name),
        },
        namespace="/snt",
        room="/all/new",
    )

    # 5 - send pm to parent
    if parentcid:
        parent = SubPostComment.get(SubPostComment.cid == parentcid)
        notif_to = parent.uid_id
        ntype = "COMMENT_REPLY"
    else:
        notif_to = post.uid_id
        ntype = "POST_REPLY"

    if notif_to != uid and uid not in misc.get_ignores(notif_to):
        notifications.send(
            ntype,
            sub=post.sid,
            post=post.pid,
            comment=comment.cid,
            sender=uid,
            target=notif_to,
        )

    # 6 - Process mentions
    sub = Sub.get_by_id(post.sid)
    misc.workWithMentions(content, notif_to, post, sub, cid=comment.cid, c_user=user)

    # Return the comment data
    comm = (
        SubPostComment.select(
            SubPostComment.cid,
            SubPostComment.content,
            SubPostComment.lastedit,
            SubPostComment.score,
            SubPostComment.status,
            SubPostComment.time,
            SubPostComment.pid,
            User.name.alias("user"),
            SubPostCommentVote.positive,
            User.status.alias("userstatus"),
            SubPostComment.upvotes,
            SubPostComment.downvotes,
        )
        .join(User, on=(User.uid == SubPostComment.uid))
        .switch(SubPostComment)
        .join(
            SubPostCommentVote,
            JOIN.LEFT_OUTER,
            on=(
                (SubPostCommentVote.uid == uid)
                & (SubPostCommentVote.cid == SubPostComment.cid)
            ),
        )
        .where(SubPostComment.cid == comment.cid)
        .dicts()[0]
    )
    comm["source"] = comm["content"]
    comm["content"] = misc.our_markdown(comm["content"])
    return jsonify(comment=comm), 200


@API.route("/post/<_sub>/<int:pid>/comment/<cid>", methods=["PATCH"])
@jwt_required
def edit_comment(_sub, pid, cid):
    """ Edits a comment """
    uid = get_jwt_identity()
    if not request.is_json:
        return jsonify(msg="Missing JSON in request"), 400

    content = request.json.get("content", None)
    if not content:
        return jsonify(msg="Content parameter required"), 400

    try:
        post = SubPost.get(SubPost.pid == pid)
    except SubPost.DoesNotExist:
        return jsonify(msg="Post not found"), 404
    # Fetch the comment
    try:
        comment = SubPostComment.get(
            (SubPostComment.pid == pid) & (SubPostComment.cid == cid)
        )
    except SubPostComment.DoesNotExist:
        return jsonify(msg="Comment not found"), 404

    if comment.uid_id != uid:
        return jsonify(msg="Unauthorized"), 403

    if post.is_archived():
        return jsonify(msg="Post is archived"), 400

    if len(content) > 16384:
        return jsonify(msg="Content is too long"), 400

    comment.content = content
    comment.lastedit = datetime.datetime.utcnow()
    comment.save()
    # TODO: move this block to a function
    comm = (
        SubPostComment.select(
            SubPostComment.cid,
            SubPostComment.content,
            SubPostComment.lastedit,
            SubPostComment.score,
            SubPostComment.status,
            SubPostComment.time,
            SubPostComment.pid,
            User.name.alias("user"),
            SubPostCommentVote.positive,
            User.status.alias("userstatus"),
            SubPostComment.upvotes,
            SubPostComment.downvotes,
        )
        .join(User, on=(User.uid == SubPostComment.uid))
        .switch(SubPostComment)
        .join(
            SubPostCommentVote,
            JOIN.LEFT_OUTER,
            on=(
                (SubPostCommentVote.uid == uid)
                & (SubPostCommentVote.cid == SubPostComment.cid)
            ),
        )
        .where(SubPostComment.cid == comment.cid)
        .dicts()[0]
    )
    comm["source"] = comm["content"]
    comm["content"] = misc.our_markdown(comm["content"])
    return jsonify(comment=comm), 200


@API.route("/post/<_sub>/<int:pid>/comment/<cid>", methods=["DELETE"])
@jwt_required
def delete_comment(_sub, pid, cid):
    uid = get_jwt_identity()

    try:
        post = SubPost.get(SubPost.pid == pid)
    except SubPost.DoesNotExist:
        return jsonify(msg="Post not found"), 404
    # Fetch the comment
    try:
        comment = SubPostComment.get(
            (SubPostComment.pid == pid) & (SubPostComment.cid == cid)
        )
    except SubPostComment.DoesNotExist:
        return jsonify(msg="Comment not found"), 404

    if comment.uid_id != uid:
        return jsonify(msg="Unauthorized"), 403

    if post.is_archived():
        return jsonify(msg="Post is archived"), 400

    comment.status = 1
    comment.save()

    return jsonify(), 200


@API.route("/post/<_sub>/<int:_pid>/comment/<cid>/vote", methods=["POST"])
@jwt_required
def vote_comment(_sub, _pid, cid):
    """ Logs an upvote to a post. """
    uid = get_jwt_identity()
    value = request.json.get("upvote", None)
    if type(value) is not bool:
        return jsonify(msg="Upvote must be true or false"), 400

    return misc.cast_vote(uid, "comment", cid, value)


@API.route("/post/<_sub>/<int:pid>/comment/<cid>/children", methods=["GET"])
def get_post_comment_children(_sub, pid, cid):
    """if key is not present, load all children for cid.
    if key is present, load all comments after (???) index `key`

    NOTE: This is a crappy solution since comment sorting might change when user is
    seeing the page and we might end up re-sending a comment (will show as duplicate).
    This can be solved by the front-end checking if a cid was already rendered, but it
    is a horrible solution
    """
    lim = request.args.get("key", default="")
    try:
        post = SubPost.get(SubPost.pid == pid)
    except SubPost.DoesNotExist:
        return jsonify(msg="Post does not exist"), 404
    if cid == "null":
        cid = "0"
    if cid != "0":
        try:
            root = SubPostComment.get(SubPostComment.cid == cid)
            if root.pid_id != post.pid:
                return jsonify(msg="Comment does not belong to the given post"), 400
        except SubPostComment.DoesNotExist:
            return jsonify(msg="Post does not exist"), 404

    comments = (
        SubPostComment.select(SubPostComment.cid, SubPostComment.parentcid)
        .where(SubPostComment.pid == pid)
        .order_by(SubPostComment.score.desc())
        .dicts()
    )
    if not comments.count():
        return jsonify(comments=[])

    if lim:
        if cid == "0":
            cid = None
        comment_tree = misc.get_comment_tree(pid, post.sid.get_id(), comments, cid, lim)
    elif cid != "0":
        comment_tree = misc.get_comment_tree(pid, post.sid.get_id(), comments, cid)
    else:
        return jsonify(msg="Illegal comment id"), 400
    return jsonify(comments=comment_tree)


class ChallengeRequired(Exception):
    """ Raised when a challenge is required. Catched by the error handlers below """

    pass


class ChallengeWrong(Exception):
    """ Raised when a challenge's solution is wrong. Catcher by the error handlers below """

    pass


@API.errorhandler(ChallengeRequired)
def chall_required(_error):
    return jsonify(msg="Challenge required"), 423


@API.errorhandler(ChallengeWrong)
def chall_wrong(_error):
    return jsonify(msg="Invalid response", failed=True), 423


def check_challenge():
    if config.app.development:
        return True
    if config.site.require_captchas:
        challenge_token = request.json.get("challengeToken")
        challenge_response = request.json.get("challengeResponse")

        if not challenge_token or not challenge_response:
            raise ChallengeRequired

        if not misc.validate_captcha(challenge_token, challenge_response):
            raise ChallengeWrong
    return True


@API.route("/challenge", methods=["GET"])
def get_challenge():
    challenge = misc.create_captcha()
    token, blob = (None, None) if challenge is None else challenge
    return jsonify(challenge_token=token, challenge_blob=blob)


@API.route("/post", methods=["POST"])
@jwt_required
@ratelimit(POSTING_LIMIT)
def create_post():
    uid = get_jwt_identity()
    if not request.is_json:
        return jsonify(msg="Missing JSON in request"), 400

    sub = request.json.get("sub", None)
    ptype = request.json.get("type", None)
    title = request.json.get("title", None)
    link = request.json.get("link", None)
    content = request.json.get("content", None)
    nsfw = request.json.get("nsfw", False)

    if not sub or ptype is None or not title:
        return jsonify(msg="Missing required parameters"), 400

    if ptype not in ("link", "upload", "text", "poll"):
        return jsonify(msg="Illegal value for ptype"), 400

    # TODO: Polls, uploads
    if ptype in ("poll", "upload"):
        return jsonify(msg="This method does not support poll creation"), 400

    try:
        user = User.get(User.uid == uid)
    except User.DoesNotExist:
        return jsonify(msg="Unknown error. User disappeared"), 403

    # TODO: Exception for admins
    if not config.site.enable_posting:
        return jsonify(msg="Posting has been temporarily disabled"), 400

    try:
        sub = Sub.get(fn.Lower(Sub.name) == sub.lower())
    except Sub.DoesNotExist:
        return jsonify(msg="Sub does not exist"), 404

    # TODO: Make this a blacklist setting in the config file?
    if sub.name.lower() in ("all", "new", "hot", "top", "admin", "home"):
        return jsonify(msg="You can't post on this sub"), 403

    subdata = misc.getSubData(sub.sid, simple=True)

    if subdata.get(misc.ptype_names[ptype], "0") == "0":
        return jsonify(msg="This sub does not allow this ptype"), 403

    if misc.is_sub_banned(sub, uid=uid):
        return jsonify(msg="You're banned from this sub"), 403

    if subdata.get("restricted", 0) == "1":
        return jsonify(msg="Only moderators can post on this sub"), 403

    if len(title.strip(misc.WHITESPACE)) < 3:
        return jsonify(msg="Post title is too short"), 400

    if len(title) > 255:
        return jsonify(msg="Post title is too long"), 400

    if misc.get_user_level(uid)[0] < 7:
        today = datetime.datetime.utcnow() - datetime.timedelta(days=1)
        lposts = (
            SubPost.select()
            .where(SubPost.uid == uid)
            .where(SubPost.sid == sub.sid)
            .where(SubPost.posted > today)
            .count()
        )
        tposts = (
            SubPost.select()
            .where(SubPost.uid == uid)
            .where(SubPost.posted > today)
            .count()
        )
        if lposts > 10 or tposts > 25:
            return jsonify(msg="You have posted too much today"), 403
    post_type = 0
    if ptype == "link":
        post_type = 1
        if not link:
            return jsonify(msg="No link provided"), 400

        if content:
            return jsonify(msg="Link posts do not accept content"), 400

        if misc.is_domain_banned(link, domain_type="link"):
            return jsonify(msg="Link's domain is banned"), 400

        recent = datetime.datetime.utcnow() - datetime.timedelta(days=5)
        try:
            wpost = (
                SubPost.select()
                .where(SubPost.sid == sub.sid)
                .where(SubPost.link == link)
            )
            wpost.where(SubPost.deleted == 0).where(SubPost.posted > recent).get()
            return (
                jsonify(msg="This link has already been posted recently on this sub"),
                403,
            )
        except SubPost.DoesNotExist:
            pass
    elif ptype == "text":
        post_type = 0
        if link:
            return jsonify(msg="Text posts do not accept link"), 400
        if len(content) > 16384:
            return jsonify(msg="Post content is too long"), 400

    if misc.get_user_level(user.uid)[0] <= 4:
        check_challenge()

    post = SubPost.create(
        sid=sub.sid,
        uid=uid,
        title=title.strip(misc.WHITESPACE),
        content=content,
        link=link if ptype == "link" else None,
        posted=datetime.datetime.utcnow(),
        score=1,
        upvotes=1,
        downvotes=0,
        deleted=0,
        comments=0,
        ptype=post_type,
        nsfw=nsfw if not subdata.get("nsfw") == "1" else 1,
        thumbnail="deferred" if ptype == "link" else "",
    )
    if ptype == "link":
        tasks.create_thumbnail_external(link, [(SubPost, "pid", post.pid)])

    Sub.update(posts=Sub.posts + 1).where(Sub.sid == sub.sid).execute()
    addr = url_for("sub.view_post", sub=sub.name, pid=post.pid)
    posts = misc.getPostList(
        misc.postListQueryBase(nofilter=True).where(SubPost.pid == post.pid), "new", 1
    ).dicts()

    defaults = [
        x.value for x in SiteMetadata.select().where(SiteMetadata.key == "default")
    ]
    ss_default = sub.sid in defaults or not config.site.recent_activity.defaults_only
    socketio.emit(
        "thread",
        {
            "addr": addr,
            "sub": sub.name,
            "type": post_type,
            "show_sidebar": ss_default
            and not config.site.recent_activity.comments_only,
            "user": user.name,
            "pid": post.pid,
            "sid": sub.sid,
            "title": post.title,
            "post_url": url_for("sub.view_post", sub=sub.name, pid=post.pid),
            "sub_url": url_for("sub.view_sub", sub=sub.name),
            "html": misc.engine.get_template("shared/post.html").render(
                {"posts": posts, "sub": False}
            ),
        },
        namespace="/snt",
        room="/all/new",
    )

    SubPostVote.create(uid=uid, pid=post.pid, positive=True)
    User.update(given=User.given + 1).where(User.uid == uid).execute()

    misc.workWithMentions(content, None, post, sub, c_user=user)
    misc.workWithMentions(title, None, post, sub, c_user=user)

    socketio.emit(
        "yourvote",
        {"pid": post.pid, "status": 1, "score": post.score},
        namespace="/snt",
        room="user" + user.name,
    )

    return jsonify(status="ok", pid=post.pid, sub=sub.name)


@API.route("/sub", methods=["GET"])
def search_sub():
    """Search for subs matching the query parameter.  Return, for each sub
    found, its name and a list of the post types allowed."""
    query = request.args.get("query", "")
    if len(query) < 3 or not misc.allowedNames.match(query):
        return jsonify(results=[])

    query = "%" + query + "%"
    subs = Sub.select(Sub.name).where(Sub.name ** query).limit(10).dicts()

    return jsonify(results=list(subs))


@API.route("/sub/<name>", methods=["GET"])
def get_sub(name):
    try:
        sub = Sub.get(fn.Lower(Sub.name) == name.lower())
    except Sub.DoesNotExist:
        return jsonify(error="Sub does not exist"), 404

    post_types = (
        SubMetadata.select()
        .where(SubMetadata.sid == sub.sid)
        .where(SubMetadata.key << set(misc.ptype_names.values()))
        .where(SubMetadata.value == "1")
    )

    allowed_post_types = {k: False for k in misc.ptype_names.keys()}
    ptype_mapping = {i: j for j, i in misc.ptype_names.items()}
    for ptype in post_types:
        allowed_post_types[ptype_mapping[ptype.key]] = True

    return jsonify(
        {
            "name": sub.name,
            "title": sub.title,
            "creation": sub.creation,
            "subscribers": sub.subscribers,
            "posts": sub.posts,
            "postTypes": allowed_post_types,
        }
    )


@API.route("/sub/rules", methods=["GET"])
def get_sub_rules():
    pid = request.args.get("pid", "")
    sub = (
        SubPost.select()
        .where(SubPost.pid == pid)
        .join(Sub)
        .where(Sub.sid == SubPost.sid)
        .dicts()
        .get()
    )
    rules = list(SubRule.select().where(SubRule.sid == sub["sid"]).dicts())

    return jsonify(results=rules)


@API.route("/user/<username>", methods=["GET"])
def get_user(username, uid=False):
    """ Returns user profile data """
    if not uid:
        try:
            user = (
                User.select()
                .where((User.status == 0) & (fn.Lower(User.name) == username.lower()))
                .get()
            )
        except User.DoesNotExist:
            return jsonify(msg="User does not exist"), 404
    else:
        user = User.get(User.uid == username)

    level = misc.get_user_level(user.uid, user.score)
    pcount = SubPost.select().where(SubPost.uid == user.uid).count()
    ccount = SubPostComment.select().where(SubPostComment.uid == user.uid).count()

    modsquery = (
        SubMod.select(Sub.name, SubMod.power_level)
        .join(Sub)
        .where((SubMod.uid == user.uid) & (~SubMod.invite))
    )
    owns = [x.sub.name for x in modsquery if x.power_level == 0]
    mods = [x.sub.name for x in modsquery if 1 <= x.power_level <= 2]
    return jsonify(
        user={
            "name": user.name,
            "score": user.score,
            "given": user.given,
            "joindate": user.joindate,
            "level": level[0],
            "xp": level[1],
            "badges": list(badges.badges_for_user(user.uid).dicts()),
            "posts": pcount,
            "comments": ccount,
            "subs": {"owns": owns, "mods": mods},
        }
    )


@API.route("/user/<username>/overview", methods=["GET"])
def user_overview(username):
    """
    Returns an overview of the user's activity (comments/posts)
    """
    try:
        user = User.get(fn.Lower(User.name) == username.lower())
    except User.DoesNotExist:
        return jsonify(msg="User does not exist"), 404
    page = request.args.get("page", default=1, type=int)
    posts = (
        SubPost.select(
            SubPost.pid,
            Sub.name.alias("sub"),
            SubPost.title,
            SubPost.posted,
            SubPost.flair,
            SubPost.nsfw,
            SubPost.comments,
            SubPost.ptype,
            SubPost.link,
            SubPost.content,
            SubPost.thumbnail,
            SubPost.upvotes,
            SubPost.downvotes,
        )
        .join(Sub, on=Sub.sid == SubPost.sid)
        .where(SubPost.uid == user.uid)
        .where(SubPost.deleted == 0)
        .paginate(page, 10)
        .order_by(SubPost.pid.desc())
        .dicts()
    )

    comments = (
        SubPostComment.select(
            SubPostComment.upvotes,
            SubPostComment.downvotes,
            SubPostComment.content,
            SubPostComment.time,
            SubPostComment.lastedit,
            SubPost.pid,
            SubPost.title.alias("post_title"),
            Sub.name.alias("sub_name"),
        )
        .join(SubPost, on=SubPostComment.pid == SubPost.pid)
        .join(Sub, on=Sub.sid == SubPost.sid)
        .where(SubPostComment.uid == user.uid)
        .where(SubPostComment.status.is_null())
        .paginate(page, 10)
        .order_by(SubPostComment.time.desc())
        .dicts()
    )

    return jsonify(posts=list(posts), comments=list(comments))


@API.route("/user", methods=["GET"])
@jwt_required
def get_own_user():
    """ Return user info and notifications count for the current user """
    uid = get_jwt_identity()
    mcount = Message.select(fn.Count(Message.mid)).where(
        (Message.receivedby == uid) & (Message.mtype == 1) & Message.read.is_null(True)
    )
    ncount = Notification.select(fn.Count(Notification.id)).where(
        (Notification.target == uid) & Notification.read.is_null(True)
    )
    user = User.select(mcount.alias("messages"), ncount.alias("notifications"))
    user = user.where(User.uid == uid).dicts().get()
    return jsonify(
        {
            "user": None,  # TODO: send same stuff as get_user
            "alerts": misc.get_notification_count(uid),
        }
    )


@API.route("/notifications", methods=["GET"])
@jwt_required
def get_notifications():
    uid = get_jwt_identity()
    page = request.args.get("page", default=1, type=int)
    autoMarkAsRead = request.args.get("autoMarkAsRead", default=True, type=bool)
    notification_list = notifications.get_notifications(uid, page)
    for ntf in notification_list:
        ntf["comment_content"] = (
            misc.our_markdown(ntf["comment_content"])
            if ntf["comment_content"]
            else None
        )
        ntf["comment_context"] = (
            misc.our_markdown(ntf["comment_context"])
            if ntf["comment_context"]
            else None
        )
        if ntf["type"] == "POST_DELETE":
            ntf["post_content"] = None
        else:
            ntf["post_content"] = (
                misc.our_markdown(ntf["post_content"]) if ntf["post_content"] else None
            )

        if ntf["type"] in ("SUB_BAN", "SUB_UNBAN") and config.site.anonymous_modding:
            ntf["sender"] = None

    if autoMarkAsRead:
        Notification.update(read=datetime.datetime.utcnow()).where(
            (Notification.read.is_null(True)) & (Notification.target == uid)
        ).execute()
    return jsonify(notifications=notification_list)


@API.route("/notifications", methods=["DELETE"])
@jwt_required
def delete_notification():
    uid = get_jwt_identity()
    if not request.is_json:
        return jsonify(msg="Missing JSON in request"), 400

    notification_id = request.json.get("notificationId", None)
    if not notification_id:
        return jsonify(error="The notificationId parameter is required"), 400

    try:
        notification = Notification.get(
            (Notification.id == notification_id) & (Notification.target == uid)
        )
    except Notification.DoesNotExist:
        return jsonify(error="Notification does not exist"), 404

    notification.delete_instance()
    return jsonify(status="ok")


@API.route("/notifications/ignore", methods=["GET"])
@jwt_required
def get_ignored():
    """ Lists all the users the user has blocked. """
    uid = get_jwt_identity()

    ignores = UserIgnores.select(User.name, UserIgnores.date).join(
        User, on=User.uid == UserIgnores.target
    )
    ignores = ignores.where(UserIgnores.uid == uid).dicts()

    return jsonify(ignores=list(ignores))


@API.route("/notifications/ignore", methods=["POST"])
@jwt_required
def ignore_notifications():
    """ Ignores all notifications coming from a certain user. """
    uid = get_jwt_identity()
    if not request.is_json:
        return jsonify(msg="Missing JSON in request"), 400

    user = request.json.get("user", None)
    if not user:
        return jsonify(error="The user parameter is required"), 400

    try:
        user = User.get(User.name == user)
    except User.DoesNotExist:
        return jsonify(error="The user provided does not exist"), 400

    try:
        UserIgnores.get((UserIgnores.uid == uid) & (UserIgnores.target == user.uid))
        return jsonify(error="User is already blocked")
    except UserIgnores.DoesNotExist:
        pass

    UserIgnores.create(uid=uid, target=user.uid)
    return jsonify(status="ok")


@API.route("/notifications/ignore", methods=["DELETE"])
@jwt_required
def unignore_notifications():
    """ Removes an ignore. """
    uid = get_jwt_identity()
    if not request.is_json:
        return jsonify(msg="Missing JSON in request"), 400

    user = request.json.get("user", None)
    if not user:
        return jsonify(error="The user parameter is required"), 400

    try:
        user = User.get(User.name == user)
    except User.DoesNotExist:
        return jsonify(error="The user provided does not exist"), 400

    try:
        ignore = UserIgnores.get(
            (UserIgnores.uid == uid) & (UserIgnores.target == user.uid)
        )
        ignore.delete_instance()
    except UserIgnores.DoesNotExist:
        return jsonify(error="User is not blocked")

    return jsonify(status="ok")


@API.route("/messages", methods=["GET"])
@jwt_required
def get_messages():
    """ Returns an array of received messages """
    uid = get_jwt_identity()
    page = request.args.get("page", default=1, type=int)
    # autoMarkAsRead = request.args.get('autoMarkAsRead', default=True, type=bool)

    msg = misc.get_messages_inbox(page, uid=uid)

    return jsonify(messages=[message_fields_for_api(m) for m in msg])


@API.route("/messages", methods=["DELETE"])
@jwt_required
def delete_message():
    uid = get_jwt_identity()
    if not request.is_json:
        return jsonify(msg="Missing JSON in request"), 400

    message_id = request.json.get("messageId", None)
    if not message_id:
        return jsonify(error="The messageId parameter is required"), 400

    try:
        Message.get((Message.mid == message_id) & (Message.receivedby == uid))
    except Message.DoesNotExist:
        return jsonify(error="Message does not exist"), 404

    UserUnreadMessage.delete().where(
        (UserUnreadMessage.uid == uid) & (UserUnreadMessage.mid == message_id)
    ).execute()
    UserMessageMailbox.update(mailbox=MessageMailbox.DELETED).where(
        (UserMessageMailbox.uid == uid) & (UserMessageMailbox.mid == message_id)
    ).execute()

    return jsonify(status="ok")


@API.route("/messages", methods=["POST"])
@jwt_required
def send_message():
    uid = get_jwt_identity()
    if not request.is_json:
        return jsonify(msg="Missing JSON in request"), 400

    to = request.json.get("to", None)
    if not to:
        return jsonify(error="The to parameter is required"), 400

    try:
        message_to = User.get(User.name == to)
    except User.DoesNotExist:
        return jsonify(error="Recipient does not exist"), 404

    subject = request.json.get("subject", None)
    if not to:
        return jsonify(error="The subject parameter is required"), 400

    content = request.json.get("content", None)
    if not to:
        return jsonify(error="The content parameter is required"), 400

    misc.create_message(
        mfrom=uid,
        to=message_to.uid,
        subject=subject,
        content=content,
        mtype=MessageType.USER_TO_USER,
    )
    return jsonify(status="ok")


@API.route("/messages/sent", methods=["GET"])
@jwt_required
def get_sent_messages():
    """ Returns an array of sent messages """
    uid = get_jwt_identity()
    page = request.args.get("page", default=1, type=int)
    msg = misc.get_messages_sent(page, uid)

    return jsonify(messages=[message_fields_for_api(m) for m in msg])


@API.route("/messages/<int:mid>/read", methods=["POST"])
@jwt_required
def read_message(mid):
    """ Marks a message as read """
    uid = get_jwt_identity()
    try:
        Message.get((Message.mid == mid) & (Message.receivedby == uid))
    except Message.DoesNotExist:
        return jsonify(error="Message not found"), 404

    try:
        um = UserUnreadMessage.get(
            (UserUnreadMessage.uid == uid) & (UserUnreadMessage.mid == mid)
        )
    except UserUnreadMessage.DoesNotExist:
        return jsonify(status="ok")

    um.delete_instance()
    socketio.emit(
        "notification",
        {"count": misc.get_notification_count(uid)},
        namespace="/snt",
        room="user" + uid,
    )

    return jsonify(status="ok")


def message_fields_for_api(m):
    result = {k: v for k, v in m.items() if k in ["subject", "content", "posted"]}
    if "read" in m:
        result["read"] = m["read"]
    if "ignored" in m:
        result["ignored"] = m["ignored"]

    result.update(
        {
            "id": m["mid"],
            "sender": m["username"],
            "content": misc.our_markdown(m["content"]),
        }
    )
    return result


@API.route("/user/settings", methods=["GET"])
@jwt_required
def get_settings():
    """ Returns account settings """
    uid = get_jwt_identity()
    prefs = UserMetadata.select().where(UserMetadata.uid == uid)
    prefs = prefs.where(UserMetadata.key << ("labrat", "nostyles", "nsfw", "nochat"))
    prefs = {x.key: x.value for x in prefs}
    return jsonify(
        settings={
            "labrat": True if prefs.get("labrat", False) == "1" else False,
            "nostyles": True if prefs.get("nostyles", False) == "1" else False,
            "nsfw": True if prefs.get("nsfw", False) == "1" else False,
            "nochat": True if prefs.get("nochat", False) == "1" else False,
        }
    )


@API.route("/user/settings", methods=["POST"])
@jwt_required
def set_settings():
    """Changes accounts settings (excl. password/email)
    Required post parameters: settings (dict of setting options and values).
    Accepted settings options:
    labrat (bool), nostyles (bool), shownsfw (bool), nochat (bools)
    """
    uid = get_jwt_identity()
    if not request.is_json:
        return jsonify(msg="Missing JSON in request"), 400

    settings = request.json.get("settings", None)
    if not settings:
        return jsonify(msg="Missing parameters"), 400

    if [
        x for x in settings.keys() if x not in ["labrat", "nostyles", "nsfw", "nochat"]
    ]:
        return jsonify(msg="Invalid setting options sent"), 400

    # Apply settings
    qrys = []
    for sett in settings:
        value = settings[sett]
        if sett in ["labrat", "nostyles", "nsfw", "nochat"]:
            if not isinstance(settings[sett], bool):
                return jsonify(msg="Invalid type for setting"), 400
            value = "1" if value else "0"

        qrys.append(
            UserMetadata.update(value=value).where(
                (UserMetadata.key == sett) & (UserMetadata.uid == uid)
            )
        )

    [x.execute() for x in qrys]
    return jsonify()


@API.route("/grabtitle", methods=["GET"])
@ratelimit(POSTING_LIMIT)
@jwt_required
def grab_title():
    url = request.args.get("url", None)
    if not url:
        return jsonify(msg="url parameter required"), 400
    return tasks.grab_title(url), 200


@API.route("/push", methods=["POST"])
@jwt_required
def inform_push_token():
    """ Informs a new push token """
    # 1. Verify if the token is valid
    uid = get_jwt_identity()

    if not request.is_json:
        return jsonify(msg="Missing JSON in request"), 400

    token = request.json.get("token", None)
    if not token:
        return jsonify(msg="Token parameter is required"), 400

    if not notifications.push_service:
        return jsonify(msg="Feature not available"), 400

    tokenData = notifications.push_service.get_registration_id_info(token)
    if not tokenData:
        return jsonify(msg="Invalid token"), 400
    # 2. Subscribe the token to the UID's topic
    foo = notifications.push_service.subscribe_registration_ids_to_topic([token], uid)
    return jsonify(res=foo, topic=uid)
