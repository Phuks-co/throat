""" Manages notifications """
from datetime import datetime, timedelta
from peewee import JOIN
from flask_babel import _
from pyfcm import FCMNotification
from .config import config
from .models import (
    Notification,
    User,
    UserMetadata,
    UserContentBlock,
    Sub,
    SubMod,
    SubPost,
    SubPostComment,
    SubPostCommentVote,
    SubPostCommentView,
    SubPostVote,
)
from .socketio import socketio
from .misc import get_notification_count, send_email
from flask import url_for


class Notifications(object):
    def __init__(self):
        self.push_service = None

    def init_app(self, app):
        with app.app_context():
            if config.notifications.fcm_api_key:
                self.push_service = FCMNotification(
                    api_key=config.notifications.fcm_api_key
                )

    @staticmethod
    def get_notifications(uid, page):
        ParentComment = SubPostComment.alias()
        SubModCurrentUser = SubMod.alias()
        notifications = (
            Notification.select(
                Notification.id,
                Notification.type,
                Notification.read,
                Notification.created,
                Sub.sid,
                Sub.name.alias("sub_name"),
                Sub.nsfw.alias("sub_nsfw"),
                Notification.post.alias("pid"),
                Notification.comment.alias("cid"),
                User.name.alias("sender"),
                Notification.sender.alias("senderuid"),
                Notification.content,
                SubPost.title.alias("post_title"),
                SubPost.posted,
                SubPost.nsfw,
                SubPostComment.content.alias("comment_content"),
                SubPostComment.score.alias("comment_score"),
                SubPostComment.content.alias("post_comment"),
                SubPostCommentView.id.alias("already_viewed"),
                SubPost.score.alias("post_score"),
                SubPost.link.alias("post_link"),
                ParentComment.content.alias("comment_context"),
                ParentComment.time.alias("comment_context_posted"),
                ParentComment.score.alias("comment_context_score"),
                ParentComment.cid.alias("comment_context_cid"),
                SubPost.content.alias("post_content"),
            )
            .join(Sub, JOIN.LEFT_OUTER)
            .switch(Notification)
            .join(SubPost, JOIN.LEFT_OUTER)
            .switch(Notification)
            .join(SubPostComment, JOIN.LEFT_OUTER)
            .join(
                SubPostCommentView,
                JOIN.LEFT_OUTER,
                on=(
                    (SubPostCommentView.cid == SubPostComment.cid)
                    & (SubPostCommentView.uid == uid)
                ),
            )
            .switch(Notification)
            .join(User, JOIN.LEFT_OUTER, on=Notification.sender == User.uid)
            .join(
                UserContentBlock,
                JOIN.LEFT_OUTER,
                on=(
                    (UserContentBlock.uid == uid)
                    & (UserContentBlock.target == User.uid)
                ),
            )
            .join(
                SubMod,
                JOIN.LEFT_OUTER,
                on=(
                    (SubMod.user == User.uid)
                    & (SubMod.sub == Notification.sub)
                    & ~SubMod.invite
                ),
            )
            .join(
                SubModCurrentUser,
                JOIN.LEFT_OUTER,
                on=(
                    (SubModCurrentUser.user == uid)
                    & (SubModCurrentUser.sub == Notification.sub)
                    & ~SubModCurrentUser.invite
                ),
            )
            .join(
                ParentComment,
                JOIN.LEFT_OUTER,
                on=(SubPostComment.parentcid == ParentComment.cid),
            )
            .where(
                (Notification.target == uid)
                & (SubPostComment.status.is_null(True))
                & (
                    UserContentBlock.id.is_null(True)
                    | ~(
                        Notification.type
                        << [
                            "POST_REPLY",
                            "COMMENT_REPLY",
                            "POST_MENTION",
                            "COMMENT_MENTION",
                        ]
                    )
                    | SubMod.sid.is_null(False)
                    | SubModCurrentUser.sid.is_null(False)
                )
            )
            .order_by(Notification.created.desc())
            .paginate(page, 50)
            .dicts()
        )
        notifications = list(notifications)
        # Fetch the votes for only the 50 notifications on the page.
        # Joining the vote tables in the query above was causing Postgres
        # to do a lot of extra work for users with many notifications and
        # votes.
        votes = (
            Notification.select(
                Notification.id,
                SubPostCommentVote.positive.alias("comment_positive"),
                SubPostVote.positive.alias("post_positive"),
            )
            .join(SubPost, JOIN.LEFT_OUTER)
            .join(
                SubPostVote,
                JOIN.LEFT_OUTER,
                on=(SubPostVote.uid == uid) & (SubPostVote.pid == SubPost.pid),
            )
            .switch(Notification)
            .join(SubPostComment, JOIN.LEFT_OUTER)
            .join(
                SubPostCommentVote,
                JOIN.LEFT_OUTER,
                on=(
                    (SubPostCommentVote.uid == uid)
                    & (SubPostCommentVote.cid == SubPostComment.cid)
                ),
            )
            .where(Notification.id << [n["id"] for n in notifications])
        ).dicts()
        votes_by_id = {v["id"]: v for v in votes}
        for n in notifications:
            n["comment_positive"] = votes_by_id[n["id"]]["comment_positive"]
            n["post_positive"] = votes_by_id[n["id"]]["post_positive"]
        return notifications

    @staticmethod
    def mark_read(uid, notifs=None):
        if notifs:
            # Help the users who can't be bothered to delete their
            # notifications by removing anything over a month old
            # unless it appears on the first page of notifications.
            Notification.delete().where(
                (Notification.target == uid)
                & (Notification.created < datetime.utcnow() - timedelta(days=30))
                & ~(Notification.id << [n["id"] for n in notifs])
            ).execute()
        Notification.update(read=datetime.utcnow()).where(
            (Notification.read.is_null(True)) & (Notification.target == uid)
        ).execute()

    @staticmethod
    def email_template(notification_type, user, post, sub):
        server_name = config.site.server_name
        def generate_external_url(url):
            return '/'.join(('https:/',server_name,*url.split("/")[-2:]))

        user_url = generate_external_url(url_for("user.view", user=user.name, _scheme="https", _external=True))
        post_url = generate_external_url(url_for(
            "sub.view_post", sub=sub.name, pid=post.pid, _scheme="https", _external=True
        ))
        sub_url = generate_external_url(url_for("sub.view_sub", sub=sub.name, _scheme="https", _external=True))
        if notification_type == "POST_REPLY":
            return _(
                ' <a clicktracking=off href="{}">{}</a> replied to your post'
                '  <a clicktracking=off href="{}">{}</a>'
                ' in  <a clicktracking=off href="{}">{}</a>'.format(
                    user_url, user.name, post_url, post.title, sub_url, sub.name
                )
            )
        elif notification_type == "COMMENT_REPLY":
            return _(
                ' <a clicktracking=off href="{}">{}'
                "</a> replied to your comment in the post titled"
                '  <a clicktracking=off href="{}">{}></a>'
                ' in  <a clicktracking=off href="{}">{}</a>'.format(
                    user_url, user.name, post_url, post.title, sub_url, sub.title
                )
            )
        elif notification_type in ("POST_MENTION", "COMMENT_MENTION"):
            return _(
                ' <a clicktracking=off href="{}">{}</a>'
                ' mentioned you in  <a clicktracking=off href="{}">{}</a>'.format(
                    user_url, user.name, post_url, post.title
                )
            )
        elif notification_type == "SUB_BAN":
            if config.site.anonymous_modding:
                return _(
                    'You have been banned from  <a clicktracking=off href="{}">{}</a>'.format(
                        sub_url, sub.name
                    )
                )
            else:
                return _(
                    ' <a clicktracking=off href="{}">{}</a> banned you from  <a clicktracking=off href="{}">{}</a>'.format(
                        user_url, user.name, sub_url, sub.name
                    )
                )
        elif notification_type == "SUB_UNBAN":
            if config.site.anonymous_modding:
                return _(
                    'You have been unbanned from  <a clicktracking=off href="{}">{}</a>'.format(
                        sub_url, sub.name
                    )
                )
            else:
                return _(
                    ' <a clicktracking=off href="{}">{}</a> unbanned you from  <a clicktracking=off href="{}">{}</a>'.format(
                        user_url, user.name, sub_url, sub.name
                    )
                )
        elif notification_type in (
            "MOD_INVITE",
            "MOD_INVITE_JANITOR",
            "MOD_INVITE_OWNER",
        ):
            return _(
                ' <a clicktracking=off href="{}">{}</a> invited you to moderate  <a clicktracking=off href="{}">{}</a>'.format(
                    user_url, user.name, sub_url, sub.name
                )
            )
        elif notification_type == "POST_DELETE":
            if config.site.anonymous_modding:
                return _(
                    'Your post  <a clicktracking=off href="{}">{}</a> has been deleted'.format(
                        post_url, post.title
                    )
                )
            else:
                return _(
                    ' <a clicktracking=off href="{}">{}</a>deleted one of your posts in  <a clicktracking=off href="{}">{}</a>'.format(
                        user_url, user.name, sub_url, sub.name
                    )
                )
        elif notification_type == "POST_UNDELETE":
            if config.site.anonymous_modding:
                return _(
                    'Your post  <a clicktracking=off href="{}">{}</a> has been un-deleted'.format(
                        post_url, post.title
                    )
                )
            else:
                return _(
                    ' <a clicktracking=off href="{}">{}</a> un-deleted one of your posts in  <a clicktracking=off href="{}">{}</a>'.format(
                        user_url, user.name, sub_url, sub.name
                    )
                )

    def send(
        self,
        notification_type,
        target,
        sender,
        sub=None,
        comment=None,
        post=None,
        content=None,
    ):
        """
        Sends a notification to an user
        @param notification_type: Type of notification. May be one of:
         - POST_REPLY
         - COMMENT_REPLY
         - POST_MENTION
         - COMMENT_MENTION
         - POST_DELETE
         - POST_UNDELETE
         - SUB_BAN
         - SUB_UNBAN
         - MOD_INVITE
         - MOD_INVITE_JANITOR
        @param target: UID of the user receiving the message
        @param sender: UID of the user sending the message or None if it was sent by the system
        @param sub: SID of the sub related to this message
        @param comment: CID of the comment related to this message
        @param post: PID of the post related to this message
        @param content: Text content of the message
        """
        Notification.create(
            type=notification_type,
            target=target,
            sender=sender,
            sub=sub,
            comment=comment,
            post=post,
            content=content,
        )

        ignore = None
        target_email_notify = (
            UserMetadata.select(UserMetadata.value).where(
                (UserMetadata.uid == target & UserMetadata.key == "email_notify")
            )
            == "1"
        )
        if target_email_notify:
            email = self.email_template(
                notification_type,
                User.get_by_id(pk=target),
                SubPost.get_by_id(pk=post),
                Sub.get_by_id(pk=sub),
            )
            send_email(
                User.get_by_id(pk=target).email,
                subject=_("New notification."),
                text_content="",
                html_content=email,
            )

        if notification_type in [
            "POST_REPLY",
            "COMMENT_REPLY",
            "POST_MENTION",
            "COMMENT_MENTION",
        ]:
            try:
                TargetSubMod = SubMod.alias()
                ignore = (
                    UserContentBlock.select()
                    .join(
                        SubMod,
                        JOIN.LEFT_OUTER,
                        on=(
                            (SubMod.uid == UserContentBlock.uid)
                            & (SubMod.sub == sub)
                            & ~SubMod.invite
                        ),
                    )
                    .join(
                        TargetSubMod,
                        JOIN.LEFT_OUTER,
                        on=(
                            (TargetSubMod.uid == UserContentBlock.target)
                            & (TargetSubMod.sub == sub)
                            & ~TargetSubMod.invite
                        ),
                    )
                    .where(
                        (UserContentBlock.target == sender)
                        & (UserContentBlock.uid == target)
                        & SubMod.uid.is_null()
                        & TargetSubMod.uid.is_null()
                    )
                ).get()
            except UserContentBlock.DoesNotExist:
                pass

        if ignore is not None:
            return

        notification_count = get_notification_count(target)
        socketio.emit(
            "notification",
            {"count": notification_count},
            namespace="/snt",
            room="user" + target,
        )
        if self.push_service:
            if sender:
                sender = User.get(User.uid == sender)

            if sub:
                sub = Sub.get(Sub.sid == sub)

            if post:
                post = SubPost.get(SubPost.pid == post)
            # TODO: Set current language to target's lang
            message_body = _(
                "Looks like nobody bothered to code the message for this notification :("
            )
            message_title = _("New notification.")
            if notification_type == "POST_REPLY":
                message_title = _(
                    "Post reply in %(prefix)s/%(sub)s",
                    prefix=config.site.sub_prefix,
                    sub=sub.name,
                )
                message_body = _(
                    "%(name)s replied to your post titled %(title)s",
                    name=sender.name,
                    title=post.title,
                )
            elif notification_type == "COMMENT_REPLY":
                message_title = _(
                    "Comment reply in %(prefix)s/%(sub)s",
                    prefix=config.site.sub_prefix,
                    sub=sub.name,
                )
                message_body = _(
                    "%(name)s replied to your comment in the post titled %(title)s",
                    name=sender.name,
                    title=post.title,
                )
            elif notification_type in ("POST_MENTION", "COMMENT_MENTION"):
                message_title = _(
                    "You were mentioned in %(prefix)s/%(sub)s",
                    prefix=config.site.sub_prefix,
                    sub=sub.name,
                )
                message_body = _(
                    "%(name)s mentioned you in the post titled %(title)s",
                    name=sender.name,
                    title=post.title,
                )
            elif notification_type == "POST_DELETE":
                message_title = _(
                    "Your post in %(prefix)s/%(sub)s was deleted",
                    prefix=config.site.sub_prefix,
                    sub=sub.name,
                )
                message_body = _(
                    "%(name)s deleted your post titled %(title)s. %(comment)s",
                    name=sender.name,
                    title=post.title,
                    comment=content,
                )
            elif notification_type == "SUB_BAN":
                message_title = _(
                    "You have been banned from %(prefix)s/%(sub)s",
                    prefix=config.site.sub_prefix,
                    sub=sub.name,
                )
                message_body = _(
                    "%(name)s banned you with reason: %(content)s",
                    name=sender.name,
                    comment=content,
                )
            elif notification_type == "SUB_UNBAN":
                message_title = _(
                    "You have been unbanned from %(prefix)s/%(sub)s",
                    prefix=config.site.sub_prefix,
                    sub=sub.name,
                )
                message_body = _("%(name)s unbanned you.", name=sender.name)
            elif notification_type in ("MOD_INVITE", "MOD_INVITE_JANITOR"):
                message_title = _(
                    "You have been invited to moderate %(prefix)s/%(sub)s",
                    prefix=config.site.sub_prefix,
                    sub=sub.name,
                )
                message_body = _(
                    "%(name)s invited you to the sub's mod team", name=sender.name
                )

            # TODO: click_action (URL the notification sends you to)
            # - Blocker: Implementing messaging in PWA
            # TODO: actions (mark as read?)
            notification_data = {
                "type": "notification",
                "title": message_title,
                "notificationPayload": {
                    "badge": config.site.icon_url,
                    "body": message_body,
                },
                "notificationCount": notification_count,
            }
            self.push_service.topic_subscribers_data_message(
                topic_name=target, data_message=notification_data
            )


notifications = Notifications()
