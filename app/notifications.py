""" Manages notifications """

from peewee import JOIN
from flask_babel import _
from pyfcm import FCMNotification
from .config import config
from .models import (
    Notification,
    User,
    UserContentBlock,
    Sub,
    SubMod,
    SubPost,
    SubPostComment,
    SubPostCommentVote,
    SubPostVote,
)
from .socketio import socketio
from .misc import get_notification_count


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
                SubPostCommentVote.positive.alias("comment_positive"),
                SubPostVote.positive.alias("post_positive"),
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
        return list(notifications)

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
