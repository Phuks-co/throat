""" All endpoints related to stuff done inside of a particular sub """
import datetime
import time
from flask import Blueprint, redirect, url_for, abort, request, Response
from flask_login import login_required, current_user
from feedgen.feed import FeedGenerator
from peewee import fn, JOIN
from ..config import config
from ..misc import engine
from ..models import (
    Sub,
    SubMetadata,
    SubStylesheet,
    SubUploads,
    SubPostComment,
    SubPost,
    SubPostPollOption,
)
from ..models import (
    SubPostPollVote,
    SubPostMetadata,
    SubFlair,
    SubLog,
    User,
    UserSaved,
    SubMod,
    SubBan,
    SubRule,
)
from ..models import (
    SubPostContentHistory,
    SubPostTitleHistory,
    SubPostReport,
    SubUserFlairChoice,
)
from ..forms import EditSubFlair, EditSubForm, EditSubCSSForm, EditMod2Form, EditSubRule
from ..forms import (
    BanUserSubForm,
    CreateSubFlair,
    PostComment,
    CreateSubRule,
    AssignSubUserFlair,
)
from .. import misc


blueprint = Blueprint("sub", __name__)


@blueprint.route("/<sub>/")
@blueprint.route("/<sub>")
def view_sub(sub):
    """ Here we can view subs """
    if sub.lower() == "all":
        return redirect(url_for("home.all_hot", page=1))

    try:
        sub = Sub.get(fn.Lower(Sub.name) == sub.lower())
    except Sub.DoesNotExist:
        abort(404)

    try:
        x = SubMetadata.select().where(SubMetadata.sid == sub.sid)
        x = x.where(SubMetadata.key == "sort").get()
        x = x.value
    except SubMetadata.DoesNotExist:
        x = "v"
    if x == "v_two":
        return redirect(url_for("sub.view_sub_new", sub=sub.name))
    elif x == "v_three":
        return redirect(url_for("sub.view_sub_top", sub=sub.name))
    else:
        return redirect(url_for("sub.view_sub_hot", sub=sub.name))


@blueprint.route("/<sub>/edit/css")
@login_required
def edit_sub_css(sub):
    """ Here we can edit sub info and settings """
    try:
        sub = Sub.get(fn.Lower(Sub.name) == sub.lower())
    except Sub.DoesNotExist:
        abort(404)

    if not current_user.is_mod(sub.sid, 1) and not current_user.is_admin():
        abort(403)

    subInfo = misc.getSubData(sub.sid)
    subMods = misc.getSubMods(sub.sid)

    c = SubStylesheet.get(SubStylesheet.sid == sub.sid)

    form = EditSubCSSForm(css=c.source)
    stor = 0
    ufiles = SubUploads.select().where(SubUploads.sid == sub.sid)
    for uf in ufiles:
        stor += uf.size / 1024

    return engine.get_template("sub/css.html").render(
        {
            "sub": sub,
            "form": form,
            "error": False,
            "storage": int(stor),
            "max_storage": config.storage.sub_css_max_file_size,
            "files": ufiles,
            "subInfo": subInfo,
            "subMods": subMods,
        }
    )


@blueprint.route("/<sub>/edit/flairs")
@login_required
def edit_sub_flairs(sub):
    """ Here we manage the sub's flairs. """
    try:
        sub = Sub.get(fn.Lower(Sub.name) == sub.lower())
    except Sub.DoesNotExist:
        abort(404)

    if not current_user.is_mod(sub.sid, 1) and not current_user.is_admin():
        abort(403)

    flairs = SubFlair.select().where(SubFlair.sid == sub.sid).dicts()
    formflairs = []
    for flair in flairs:
        formflairs.append(EditSubFlair(flair=flair["xid"], text=flair["text"]))

    return engine.get_template("sub/flairs.html").render(
        {"sub": sub, "flairs": formflairs, "createflair": CreateSubFlair()}
    )


@blueprint.route("/<sub>/edit/user_flairs")
@login_required
def edit_sub_user_flairs(sub):
    """ Here we manage user flairs """
    try:
        sub = Sub.get(fn.Lower(Sub.name) == sub.lower())
    except Sub.DoesNotExist:
        abort(404)

    if not current_user.is_mod(sub.sid, 1) and not current_user.is_admin():
        abort(403)

    flairs = SubUserFlairChoice.select().where(SubUserFlairChoice.sub == sub.sid)
    # assigned_flairs = SubUserFlair.select(SubUserFlair.flair_choice, SubUserFlair.flair, User.name)\
    #     .join(User).where(SubUserFlair.sub == sub.sid).dicts()

    assignflair = AssignSubUserFlair()

    formflairs = []
    for flair in flairs:
        formflairs.append(EditSubFlair(flair=flair.id, text=flair.flair))
        assignflair.flair_id.choices.append((flair.id, flair.flair))

    # formuserflairs = []
    # for flair in assigned_flairs:
    #     formuserflairs.append(EditSubUserFlair(flair=flair['flair_choice'], text=flair['flair'], user=flair['name']))

    return engine.get_template("sub/user_flairs.html").render(
        {
            "sub": sub,
            "flairs": formflairs,
            "createflair": CreateSubFlair(),  # 'assigned_flairs': formuserflairs,
            "assignflair": assignflair,
        }
    )


@blueprint.route("/<sub>/edit/rules")
@login_required
def edit_sub_rules(sub):
    """ Here we manage the sub's rules. """
    try:
        sub = Sub.get(fn.Lower(Sub.name) == sub.lower())
    except Sub.DoesNotExist:
        abort(404)

    if not current_user.is_mod(sub.sid, 1) and not current_user.is_admin():
        abort(403)

    rules = SubRule.select().where(SubRule.sid == sub.sid).dicts()
    formrules = []
    for rule in rules:
        formrules.append(EditSubRule(rule=rule["rid"], text=rule["text"]))

    return engine.get_template("sub/rules.html").render(
        {"sub": sub, "rules": formrules, "createrule": CreateSubRule()}
    )


@blueprint.route("/<sub>/edit")
@login_required
def edit_sub(sub):
    """ Here we can edit sub info and settings """
    try:
        sub = Sub.get(fn.Lower(Sub.name) == sub.lower())
    except Sub.DoesNotExist:
        abort(404)

    if current_user.is_mod(sub.sid, 1) or current_user.is_admin():
        submeta = misc.metadata_to_dict(
            SubMetadata.select().where(SubMetadata.sid == sub.sid)
        )
        form = EditSubForm()
        # pre-populate the form.
        form.subsort.data = submeta.get("sort")
        form.sidebar.data = sub.sidebar
        form.title.data = sub.title

        return engine.get_template("sub/settings.html").render(
            {"sub": sub, "editsubform": form, "metadata": submeta}
        )
    else:
        abort(403)


@blueprint.route("/<sub>/sublog", defaults={"page": 1})
@blueprint.route("/<sub>/sublog/<int:page>")
def view_sublog(sub, page):
    """ Here we can see a log of mod/admin activity in the sub """
    try:
        sub = Sub.select().where(fn.Lower(Sub.name) == sub.lower()).dicts().get()
    except Sub.DoesNotExist:
        abort(404)

    subInfo = misc.getSubData(sub["sid"])
    if not config.site.force_sublog_public:
        log_is_private = subInfo.get("sublog_private", 0) == "1"

        if log_is_private and not (
            current_user.is_mod(sub["sid"], 1) or current_user.is_admin()
        ):
            abort(404)

    subMods = misc.getSubMods(sub["sid"])
    logs = (
        SubLog.select()
        .where(SubLog.sid == sub["sid"])
        .order_by(SubLog.lid.desc())
        .paginate(page, 50)
    )
    return engine.get_template("sub/log.html").render(
        {"sub": sub, "logs": logs, "page": page, "subInfo": subInfo, "subMods": subMods}
    )


@blueprint.route("/<sub>/mods")
@login_required
def edit_sub_mods(sub):
    """ Here we can edit moderators for a sub """
    try:
        sub = Sub.get(fn.Lower(Sub.name) == sub.lower())
    except Sub.DoesNotExist:
        abort(404)

    if (
        current_user.is_mod(sub.sid, 2)
        or current_user.is_modinv(sub.sid)
        or current_user.is_admin()
    ):
        subdata = misc.getSubData(sub.sid, extra=True)
        subMods = misc.getSubMods(sub.sid)
        modInvites = (
            SubMod.select(User.name, SubMod.power_level)
            .join(User)
            .where((SubMod.sid == sub.sid) & SubMod.invite)
        )
        return engine.get_template("sub/mods.html").render(
            {
                "sub": sub,
                "subdata": subdata,
                "editmod2form": EditMod2Form(),
                "subMods": subMods,
                "subModInvites": modInvites,
            }
        )
    else:
        abort(403)


@blueprint.route("/<sub>/new.rss")
def sub_new_rss(sub):
    """ RSS feed for /sub/new """
    try:
        sub = Sub.get(fn.Lower(Sub.name) == sub.lower())
    except Sub.DoesNotExist:
        abort(404)

    fg = FeedGenerator()
    fg.id(request.url)
    fg.title("New posts from " + sub.name)
    fg.link(href=request.url_root, rel="alternate")
    fg.link(href=request.url, rel="self")

    posts = misc.getPostList(
        misc.postListQueryBase(noAllFilter=True).where(Sub.sid == sub.sid), "new", 1
    )

    return Response(
        misc.populate_feed(fg, posts).atom_str(pretty=True),
        mimetype="application/atom+xml",
    )


@blueprint.route("/<sub>/new", defaults={"page": 1})
@blueprint.route("/<sub>/new/<int:page>")
def view_sub_new(sub, page):
    """ The index page, all posts sorted as most recent posted first """
    if sub.lower() == "all":
        return redirect(url_for("home.all_new", page=1))

    flair = request.args.get("flair")

    try:
        sub = Sub.select().where(fn.Lower(Sub.name) == sub.lower()).dicts().get()
    except Sub.DoesNotExist:
        abort(404)

    isSubMod = current_user.is_mod(sub["sid"], 1) or current_user.is_admin()

    posts = misc.getPostList(
        misc.postListQueryBase(noAllFilter=True, isSubMod=isSubMod, flair=flair).where(
            Sub.sid == sub["sid"]
        ),
        "new",
        page,
    )

    return engine.get_template("sub.html").render(
        {
            "sub": sub,
            "subInfo": misc.getSubData(sub["sid"]),
            "posts": posts,
            "page": page,
            "sort_type": "sub.view_sub_new",
            "subMods": misc.getSubMods(sub["sid"]),
            "flair": flair,
        }
    )


@blueprint.route("/<sub>/bannedusers")
def view_sub_bans(sub):
    """ See banned users for the sub """
    try:
        sub = Sub.get(fn.Lower(Sub.name) == sub.lower())
    except Sub.DoesNotExist:
        abort(404)

    subInfo = misc.getSubData(sub.sid)
    if not config.site.force_sublog_public:
        banned_users_is_private = subInfo.get("sub_banned_users_private", 0) == "1"

        if banned_users_is_private and not (
            current_user.is_mod(sub.sid, 1) or current_user.is_admin()
        ):
            abort(404)

    user = User.alias()
    created_by = User.alias()
    banned = SubBan.select(
        user, created_by, SubBan.created, SubBan.reason, SubBan.expires
    )
    banned = (
        banned.join(user, on=SubBan.uid)
        .switch(SubBan)
        .join(created_by, JOIN.LEFT_OUTER, on=SubBan.created_by_id)
    )
    banned = (
        banned.where(SubBan.sid == sub.sid)
        .where(SubBan.effective)
        .where(
            (SubBan.expires.is_null(True))
            | (SubBan.expires > datetime.datetime.utcnow())
        )
    )
    banned = banned.order_by(SubBan.created.is_null(True), SubBan.created.desc())

    xbans = SubBan.select(
        user, created_by, SubBan.created, SubBan.reason, SubBan.expires
    )
    xbans = (
        xbans.join(user, on=SubBan.uid)
        .switch(SubBan)
        .join(created_by, JOIN.LEFT_OUTER, on=SubBan.created_by_id)
    )

    xbans = xbans.where(SubBan.sid == sub.sid)
    xbans = xbans.where(
        (~SubBan.effective)
        | (
            (SubBan.expires.is_null(False))
            & (SubBan.expires < datetime.datetime.utcnow())
        )
    )
    xbans = xbans.order_by(
        SubBan.created.is_null(True), SubBan.created.desc(), SubBan.expires.asc()
    )

    return engine.get_template("sub/bans.html").render(
        {
            "sub": sub,
            "banned": banned,
            "xbans": xbans,
            "banuserform": BanUserSubForm(),
            "submods": misc.getSubMods(sub.sid),
        }
    )


@blueprint.route("/<sub>/top", defaults={"page": 1})
@blueprint.route("/<sub>/top/<int:page>")
def view_sub_top(sub, page):
    """ The index page, /top sorting """
    if sub.lower() == "all":
        return redirect(url_for("home.all_top", page=1))

    flair = request.args.get("flair")

    try:
        sub = Sub.select().where(fn.Lower(Sub.name) == sub.lower()).dicts().get()
    except Sub.DoesNotExist:
        abort(404)

    isSubMod = current_user.is_mod(sub["sid"], 1) or current_user.is_admin()

    posts = misc.getPostList(
        misc.postListQueryBase(noAllFilter=True, isSubMod=isSubMod, flair=flair).where(
            Sub.sid == sub["sid"]
        ),
        "top",
        page,
    )

    return engine.get_template("sub.html").render(
        {
            "sub": sub,
            "subInfo": misc.getSubData(sub["sid"]),
            "posts": posts,
            "page": page,
            "sort_type": "sub.view_sub_top",
            "subMods": misc.getSubMods(sub["sid"]),
            "flair": flair,
        }
    )


@blueprint.route("/<sub>/hot", defaults={"page": 1})
@blueprint.route("/<sub>/hot/<int:page>")
def view_sub_hot(sub, page):
    """ The index page, /hot sorting """
    if sub.lower() == "all":
        return redirect(url_for("home.all_hot", page=1))

    flair = request.args.get("flair")

    try:
        sub = Sub.select().where(fn.Lower(Sub.name) == sub.lower()).dicts().get()
    except Sub.DoesNotExist:
        abort(404)

    isSubMod = current_user.is_mod(sub["sid"], 1) or current_user.is_admin()

    posts = misc.getPostList(
        misc.postListQueryBase(noAllFilter=True, isSubMod=isSubMod, flair=flair).where(
            Sub.sid == sub["sid"]
        ),
        "hot",
        page,
    )

    return engine.get_template("sub.html").render(
        {
            "sub": sub,
            "subInfo": misc.getSubData(sub["sid"]),
            "posts": posts,
            "page": page,
            "sort_type": "sub.view_sub_hot",
            "subMods": misc.getSubMods(sub["sid"]),
            "flair": flair,
        }
    )


@blueprint.route("/<sub>/<int:pid>", defaults={"slug": ""})
@blueprint.route("/<sub>/<int:pid>/<slug>")
def view_post(sub, pid, slug=None, comments=False, highlight=None):
    """ View post and comments (WIP) """
    sort = request.args.get("sort", default=None, type=str)
    try:
        post = misc.getSinglePost(pid)
    except SubPost.DoesNotExist:
        return abort(404)

    if post["sub"].lower() != sub.lower():
        abort(404)

    # We check the slug and correct it if it's wrong
    if slug != post["slug"]:
        kwargs = {} if sort is None else {"sort": sort}
        return redirect(
            url_for("sub.view_post", sub=sub, pid=pid, slug=post["slug"], **kwargs), 301
        )

    sub = Sub.select().where(fn.Lower(Sub.name) == sub.lower()).dicts().get()
    subInfo = misc.getSubData(sub["sid"])
    postmeta = misc.metadata_to_dict(
        SubPostMetadata.select().where(SubPostMetadata.pid == pid)
    )

    sticky_sort = "best" if post["best_sort_enabled"] else "top"
    if str(pid) in subInfo["sticky"]:
        sticky_sort = postmeta.get("sort", sticky_sort)

    if sort is None:
        sort = sticky_sort
    if sort == "best" and not post["best_sort_enabled"]:
        sort = "top"

    subMods = misc.getSubMods(sub["sid"])
    include_history = current_user.is_mod(sub["sid"], 1) or current_user.is_admin()

    if current_user.is_mod(sub["sid"], 1) or current_user.is_admin():
        open_reports = (
            SubPostReport.select()
            .where((SubPostReport.pid == pid) & SubPostReport.open)
            .dicts()
        )
    else:
        open_reports = False

    try:
        UserSaved.get((UserSaved.uid == current_user.uid) & (UserSaved.pid == pid))
        is_saved = True
    except UserSaved.DoesNotExist:
        is_saved = False

    if not comments:
        comments = misc.get_comment_query(post["pid"], sort=sort)

        if not comments.count():
            comments = []
        else:
            comments = misc.get_comment_tree(
                post["pid"],
                sub["sid"],
                comments,
                uid=current_user.uid,
                include_history=include_history,
                postmeta=postmeta,
            )

    if config.site.edit_history and include_history:
        try:
            content_history = (
                SubPostContentHistory.select(
                    SubPostContentHistory.pid,
                    SubPostContentHistory.content,
                    SubPostContentHistory.datetime,
                )
                .where(SubPostContentHistory.pid == post["pid"])
                .order_by(SubPostContentHistory.datetime.desc())
                .dicts()
            )
        except SubPostContentHistory.DoesNotExist:
            content_history = []

        try:
            title_history = (
                SubPostTitleHistory.select(
                    SubPostTitleHistory.pid,
                    SubPostTitleHistory.title,
                    SubPostTitleHistory.datetime,
                )
                .where(SubPostTitleHistory.pid == post["pid"])
                .order_by(SubPostTitleHistory.datetime.desc())
                .dicts()
            )
        except SubPostTitleHistory.DoesNotExist:
            title_history = []

    else:
        content_history = []
        title_history = []

    post["visibility"] = ""
    if post["deleted"] == 1:
        if current_user.uid == post["uid"]:
            post["visibility"] = "user-self-del"
        elif current_user.is_admin():
            post["visibility"] = "admin-self-del"
        elif current_user.is_mod(sub["sid"], 1):
            post["visibility"] = "mod-self-del"
        else:
            post["visibility"] = "none"
    elif post["deleted"] in [2, 3]:
        if current_user.is_admin() or current_user.is_mod(sub["sid"], 1):
            post["visibility"] = "mod-del" if post["deleted"] == 2 else "admin-del"
        elif current_user.uid == post["uid"]:
            post["visibility"] = "user-mod-del"
        else:
            post["visibility"] = "none"

    if post["userstatus"] == 10 and post["deleted"] == 1:
        post["visibility"] = "none"

    postmeta = misc.metadata_to_dict(
        SubPostMetadata.select().where(SubPostMetadata.pid == pid)
    )

    pollData = {"has_voted": False}
    if post["ptype"] == 3:
        # poll. grab options and votes.
        options = (
            SubPostPollOption.select(
                SubPostPollOption.id,
                SubPostPollOption.text,
                fn.Count(SubPostPollVote.id).alias("votecount"),
            )
            .join(
                SubPostPollVote,
                JOIN.LEFT_OUTER,
                on=(SubPostPollVote.vid == SubPostPollOption.id),
            )
            .where(SubPostPollOption.pid == pid)
            .group_by(SubPostPollOption.id)
            .order_by(SubPostPollOption.id)
        )
        pollData["options"] = options
        total_votes = SubPostPollVote.select().where(SubPostPollVote.pid == pid).count()
        pollData["total_votes"] = total_votes
        if current_user.is_authenticated:
            # Check if user has already voted on this poll.
            try:
                u_vote = SubPostPollVote.get(
                    (SubPostPollVote.pid == pid)
                    & (SubPostPollVote.uid == current_user.uid)
                )
                pollData["has_voted"] = True
                pollData["voted_for"] = u_vote.vid_id
            except SubPostPollVote.DoesNotExist:
                pollData["has_voted"] = False

        # Check if the poll is open
        pollData["poll_open"] = True
        if "poll_closed" in postmeta:
            pollData["poll_open"] = False

        if "poll_closes_time" in postmeta:
            pollData["poll_closes"] = datetime.datetime.utcfromtimestamp(
                int(postmeta["poll_closes_time"])
            ).isoformat()
            if int(postmeta["poll_closes_time"]) < time.time():
                pollData["poll_open"] = False

    if (post["nsfw"] or sub["nsfw"]) and (
        "nsfw" not in current_user.prefs or "nsfw_blur" in current_user.prefs
    ):
        post["blur"] = "nsfw-blur"
    else:
        post["blur"] = ""

    return engine.get_template("sub/post.html").render(
        {
            "post": post,
            "sub": sub,
            "subInfo": subInfo,
            "is_saved": is_saved,
            "pollData": pollData,
            "postmeta": postmeta,
            "commentform": PostComment(),
            "comments": comments,
            "subMods": subMods,
            "highlight": highlight,
            "content_history": content_history,
            "title_history": title_history,
            "open_reports": open_reports,
            "sort": sort,
            "sticky_sort": sticky_sort,
        }
    )


@blueprint.route("/<sub>/<int:pid>/_/<cid>", defaults={"slug": "_"})
@blueprint.route("/<sub>/<int:pid>/<slug>/<cid>")
def view_perm(sub, pid, slug, cid):
    """ Permalink to comment """
    # We get the comment...
    try:
        post = (
            SubPost.select(
                SubPost.pid,
                SubPost.sid,
                SubPost.posted,
                SubPost.title,
                Sub.name,
            )
            .join(SubPostComment)
            .switch(SubPost)
            .join(Sub)
            .where(
                (SubPostComment.cid == cid)
                & (SubPost.pid == pid)
                & (fn.Lower(Sub.name) == sub.lower())
            )
            .dicts()
            .get()
        )
    except SubPost.DoesNotExist:
        return abort(404)

    if slug != misc.slugify(post["title"]):
        return redirect(
            url_for(
                "sub.view_perm",
                sub=sub,
                pid=pid,
                slug=misc.slugify(post["title"]),
                cid=cid,
            ),
            301,
        )

    include_history = current_user.is_mod(post["sid"], 1) or current_user.is_admin()
    sort = "best" if post["posted"] > misc.get_best_comment_sort_init_date() else "top"
    comments = misc.get_comment_query(pid, sort=sort)
    comment_tree = misc.get_comment_tree(
        pid,
        post["sid"],
        comments,
        cid,
        uid=current_user.uid,
        include_history=include_history,
    )
    return view_post(post["name"], pid, slug, comment_tree, cid)
