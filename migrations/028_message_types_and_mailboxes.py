"""Peewee migrations -- 028_message_types_and_mailboxes.py

Modify the Message model to separate message mailboxes for sender and
receiver, to support multiple receivers, and to support a future
implentation of modmail.

"""

import datetime as dt
from enum import IntEnum
import peewee as pw
from decimal import ROUND_HALF_EVEN

try:
    import playhouse.postgres_ext as pw_pext
except ImportError:
    pass

SQL = pw.SQL


class MessageType(IntEnum):
    """Types of private messages.
    Value of the 'mtype' field in Message."""

    USER_TO_USER = 100
    USER_TO_MODS = 101
    MOD_TO_USER_AS_USER = 102
    MOD_TO_USER_AS_MOD = 103
    MOD_DISCUSSION = 104
    USER_BAN_APPEAL = 105
    MOD_NOTIFICATION = 106


class MessageMailbox(IntEnum):
    """Mailboxes for private messages.
    Used in UserMessageMailbox and ModMessageMailbox."""

    INBOX = 200
    SENT = 201
    SAVED = 202
    ARCHIVED = 203  # Modmail only.
    TRASH = 204
    DELETED = 205


def migrate(migrator, database, fake=False, **kwargs):
    """Write your migrations here."""

    User = migrator.orm["user"]
    Message = migrator.orm["message"]
    Sub = migrator.orm["sub"]

    @migrator.create_model
    class UserUnreadMessage(pw.Model):
        id = pw.AutoField()
        uid = pw.ForeignKeyField(db_column="uid", model=User, field="uid")
        mid = pw.ForeignKeyField(db_column="mid", model=Message, field="mid")

        class Meta:
            table_name = "user_unread_message"

    @migrator.create_model
    class UserMessageMailbox(pw.Model):
        uid = pw.ForeignKeyField(db_column="uid", model=User, field="uid")
        mid = pw.ForeignKeyField(db_column="mid", model=Message, field="mid")
        mailbox = pw.IntegerField(default=MessageMailbox.INBOX)

        class Meta:
            table_name = "user_message_mailbox"

    if not fake:
        UserUnreadMessage.create_table(True)
        UserMessageMailbox.create_table(True)
        for msg in Message.select():
            if not msg.read:
                UserUnreadMessage.create(mid=msg.mid, uid=msg.receivedby)
            old_mtype = msg.mtype
            msg.mtype = MessageType.USER_TO_USER
            msg.save()

            if old_mtype == 9:
                mailbox = MessageMailbox.SAVED
            elif old_mtype == 6:
                mailbox = MessageMailbox.DELETED
            else:
                mailbox = MessageMailbox.INBOX
            UserMessageMailbox.create(mid=msg.mid, uid=msg.receivedby, mailbox=mailbox)
            UserMessageMailbox.create(
                mid=msg.mid, uid=msg.sentby, mailbox=MessageMailbox.SENT
            )

    migrator.add_fields(
        "message",
        reply_to=pw.ForeignKeyField(
            db_column="reply_to", null=True, model="self", field="mid"
        ),
    )
    migrator.add_fields(
        "message",
        sub=pw.ForeignKeyField(db_column="sid", null=True, model=Sub, field="sid"),
    )
    migrator.add_fields("message", replies=pw.IntegerField(default=0))

    migrator.remove_fields("message", "mlink")


def rollback(migrator, database, fake=False, **kwargs):
    """Write your rollback migrations here."""

    UserMessageMailbox = migrator.orm["user_message_mailbox"]
    UserUnreadMessage = migrator.orm["user_unread_message"]
    Message = migrator.orm["message"]
    UserIgnores = migrator.orm["user_ignores"]

    now = dt.datetime.utcnow()
    if not fake:
        for msg in (
            Message.select()
            .join(
                UserUnreadMessage,
                pw.JOIN.LEFT_OUTER,
                on=(
                    (UserUnreadMessage.mid == Message.mid)
                    & (UserUnreadMessage.uid == Message.receivedby)
                ),
            )
            .where(UserUnreadMessage.mid.is_null())
        ):
            msg.read = now
            msg.save()

        query = Message.select().join(
            UserMessageMailbox,
            pw.JOIN.INNER,
            on=(
                (UserMessageMailbox.mid == Message.mid)
                & (UserMessageMailbox.uid == Message.receivedby)
            ),
        )
        for msg in query.where(UserMessageMailbox.mailbox == MessageMailbox.SAVED):
            msg.mtype = 9
            msg.save()
        for msg in query.where(UserMessageMailbox.mailbox == MessageMailbox.DELETED):
            msg.mtype = 6
            msg.save()
        for msg in query.where(UserMessageMailbox.mailbox == MessageMailbox.INBOX):
            msg.mtype = 1
            msg.save()

        for msg in Message.select().join(
            UserIgnores,
            pw.JOIN.RIGHT_OUTER,
            on=(
                (UserIgnores.uid == Message.receivedby)
                & (UserIgnores.target == Message.sentby)
            ),
        ):
            msg.mtype = 41
            msg.save()

    migrator.add_fields("message", mlink=pw.CharField(null=True))

    migrator.remove_fields("message", "reply_to")
    migrator.remove_fields("message", "sub")
    migrator.remove_fields("message", "replies")

    migrator.remove_model("user_unread_message")
    migrator.remove_model("user_message_mailbox")
    migrator.remove_model("sub_message_mailbox")
