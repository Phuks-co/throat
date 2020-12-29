""" Manages notifications """

from flask_babel import _
from pyfcm import FCMNotification
from .config import config
from .models import Notification, User, Sub, SubPost
from .socketio import socketio
from .misc import get_notification_count


class Notifications(object):
    def __init__(self):
        self.push_service = None

    def init_app(self, app):
        with app.app_context():
            if config.notifications.fcm_api_key:
                self.push_service = FCMNotification(api_key=config.notifications.fcm_api_key)

    def send(self, notification_type, target, sender, sub=None, comment=None, post=None, content=None):
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
        Notification.create(type=notification_type, target=target, sender=sender, sub=sub, comment=comment, post=post, content=content)

        socketio.emit('notification',
                      {'count': get_notification_count(target)},
                      namespace='/snt',
                      room='user' + target)
        if self.push_service:
            if sender:
                sender = User.get(User.uid == sender)

            if sub:
                sub = Sub.get(Sub.sid == sub)

            if post:
                post = SubPost.get(SubPost.pid == post)
            # TODO: Set current language to target's lang
            message_body = _("Looks like nobody bothered to code the message for this notification :(")
            message_title = _("New notification.")
            if notification_type == 'POST_REPLY':
                message_title = _("Post reply in %(prefix)s/%(sub)s", prefix=config.site.sub_prefix, sub=sub.name)
                message_body = _("%(name)s replied to your post titled %(title)s", name=sender.name, title=post.title)
            elif notification_type == 'COMMENT_REPLY':
                message_title = _("Comment reply in %(prefix)s/%(sub)s", prefix=config.site.sub_prefix, sub=sub.name)
                message_body = _("%(name)s replied to your comment in the post titled %(title)s", name=sender.name, title=post.title)
            elif notification_type in ('POST_MENTION', 'COMMENT_MENTION'):
                message_title = _("You were mentioned in %(prefix)s/%(sub)s", prefix=config.site.sub_prefix, sub=sub.name)
                message_body = _("%(name)s mentioned you in the post titled %(title)s", name=sender.name, title=post.title)
            elif notification_type == 'POST_DELETE':
                message_title = _("Your post in %(prefix)s/%(sub)s was deleted", prefix=config.site.sub_prefix, sub=sub.name)
                message_body = _("%(name)s deleted your post titled %(title)s. %(comment)s", name=sender.name, title=post.title, comment=content)
            elif notification_type == 'SUB_BAN':
                message_title = _("You have been banned from %(prefix)s/%(sub)s", prefix=config.site.sub_prefix, sub=sub.name)
                message_body = _("%(name)s banned you with reason: %(content)s", name=sender.name, comment=content)
            elif notification_type == 'SUB_UNBAN':
                message_title = _("You have been unbanned from %(prefix)s/%(sub)s", prefix=config.site.sub_prefix, sub=sub.name)
                message_body = _("%(name)s unbanned you.", name=sender.name)
            elif notification_type in ('MOD_INVITE', 'MOD_INVITE_JANITOR'):
                message_title = _("You have been invited to moderate %(prefix)s/%(sub)s", prefix=config.site.sub_prefix, sub=sub.name)
                message_body = _("%(name)s invited you to the sub's mod team", name=sender.name)

            # TODO: click_action (URL the notification sends you to)
            # - Blocker: Implementing messaging in PWA
            # TODO: actions (mark as read?)
            notification_data = {
                'type': 'notification',
                'title': message_title,
                'notificationPayload': {
                    'badge': config.site.icon_url,
                    'body': message_body
                }
            }
            self.push_service.topic_subscribers_data_message(topic_name=target, data_message=notification_data)


notifications = Notifications()
