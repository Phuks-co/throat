"""Peewee migrations -- 042_message_threads.py

Add a new model for information shared by all private messages in a
thread.  Add support for highlighted messages in modmail.

"""

import datetime as dt
import peewee as pw
from decimal import ROUND_HALF_EVEN
from enum import IntEnum

try:
    import playhouse.postgres_ext as pw_pext
except ImportError:
    pass

SQL = pw.SQL


class SubMessageLogAction(IntEnum):
    CHANGE_MAILBOX = 1
    HIGHLIGHT = 2


def migrate(migrator, database, fake=False, **kwargs):
    """Write your migrations here."""

    Message = migrator.orm["message"]
    SubMessageMailbox = migrator.orm["sub_message_mailbox"]
    SubMessageLog = migrator.orm["sub_message_log"]

    @migrator.create_model
    class MessageThread(pw.Model):
        mtid = pw.PrimaryKeyField()
        replies = pw.IntegerField(default=0)
        subject = pw.CharField()
        # Relevant for modmail messages, otherwise NULL.
        sub = pw.ForeignKeyField(
            db_column="sid", null=True, model=migrator.orm["sub"], field="sid"
        )
        # Temporary reference used during migration and then dropped.
        mid = pw.ForeignKeyField(model=Message, field="mid")

        class Meta:
            table_name = "message_thread"

    migrator.add_fields(Message, first=pw.BooleanField(default=False))
    migrator.add_fields(
        Message,
        thread=pw.ForeignKeyField(
            db_column="mtid", null=True, model=MessageThread, field="mtid"
        ),
    )
    migrator.add_fields(
        SubMessageMailbox,
        highlighted=pw.BooleanField(default=False),
        thread=pw.ForeignKeyField(
            db_column="mtid", null=True, model=MessageThread, field="mtid"
        ),
    )
    migrator.add_fields(
        SubMessageLog,
        action=pw.IntegerField(default=SubMessageLogAction.CHANGE_MAILBOX),
        thread=pw.ForeignKeyField(
            db_column="mtid", null=True, model=MessageThread, field="mtid"
        ),
        desc=pw.CharField(null=True),
    )
    migrator.drop_not_null("sub_message_log", "mailbox")

    if not fake:
        migrator.run()

        # Create MessageThread entries for each thread, and set the
        # flag for the first message in each thread.
        first_messages = Message.select(
            Message.mid, Message.replies, Message.subject, Message.sub
        ).where(Message.reply_to.is_null())

        threadmap = {}
        for msg in first_messages:
            mt = MessageThread.create(
                replies=msg.replies, subject=msg.subject, sub=msg.sub, mid=msg.mid
            )
            threadmap[mt.mid_id] = mt.mtid
            msg.thread = mt.mtid
            msg.first = True
            msg.save()

        # Set the message thread field in all reply messages.
        reply_messages = Message.select(Message.mid, Message.reply_to).where(
            Message.reply_to.is_null(False)
        )
        for msg in reply_messages:
            msg.thread = threadmap[msg.mid] = threadmap[msg.reply_to_id]
            msg.save()

        # Ensure that each modmail thread has a SubMessageMailbox record.
        sub_messages_without_mailboxes = (
            Message.select(Message.mid)
            .join(SubMessageMailbox, on=(SubMessageMailbox.mid == Message.mid))
            .where(
                Message.reply_to.is_null()
                & Message.sub.is_null(False)
                & SubMessageMailbox.id.is_null()
            )
        )
        for msg in sub_messages_without_mailboxes:
            smm = SubMessageMailbox.create(mid=msg.mid)
            smm.save()

        # Set the message thread field in all SubMessageMailbox records.
        sub_mailboxes = SubMessageMailbox.select()
        for mbox in sub_mailboxes:
            mbox.thread = threadmap[mbox.mid_id]
            mbox.save()

        # Set the message thread field in all SubMessageLog records.
        sub_logs = SubMessageLog.select()
        for log in sub_logs:
            log.thread = threadmap[log.mid_id]
            log.desc = str(log.mailbox)
            log.save()

    migrator.add_not_null("message", "thread")
    migrator.add_not_null("sub_message_mailbox", "thread")
    migrator.add_not_null("sub_message_log", "action")
    migrator.add_index("sub_message_log", "updated", unique=False)
    migrator.remove_fields("message", "reply_to", "subject", "sub", "replies")
    migrator.remove_fields("message_thread", "mid")
    migrator.remove_fields("sub_message_mailbox", "mid")
    migrator.remove_fields("sub_message_log", "mid", "mailbox")


def rollback(migrator, database, fake=False, **kwargs):
    """Write your rollback migrations here."""

    migrator.add_fields(
        "message",
        reply_to=pw.ForeignKeyField(
            db_column="reply_to", null=True, model="self", field="mid"
        ),
        sub=pw.ForeignKeyField(
            db_column="sid", null=True, model=migrator.orm["sub"], field="sid"
        ),
        replies=pw.IntegerField(default=0),
        subject=pw.CharField(null=True),
    )
    migrator.add_fields(
        "sub_message_mailbox",
        mid=pw.ForeignKeyField(
            db_column="mid", null=True, model=migrator.orm["message"], field="mid"
        ),
    )
    migrator.add_fields(
        "sub_message_log",
        mid=pw.ForeignKeyField(
            db_column="mid", null=True, model=migrator.orm["message"], field="mid"
        ),
        mailbox=pw.IntegerField(null=True),
    )

    if not fake:
        migrator.run()
        Message = migrator.orm["message"]
        MessageThread = migrator.orm["message_thread"]
        Sub = migrator.orm["sub"]
        SubMessageMailbox = migrator.orm["sub_message_mailbox"]
        SubMessageLog = migrator.orm["sub_message_log"]

        threads = (
            MessageThread.select(
                MessageThread.mtid,
                MessageThread.replies,
                MessageThread.subject,
                MessageThread.sub,
                Message.mid,
            )
            .join(Message, on=(Message.thread == MessageThread.mtid))
            .where(Message.first)
        ).dicts()

        threadmap = {}
        for t in threads:
            threadmap[t["mtid"]] = t

        messages = Message.select(
            Message.mid,
            Message.mtid,
            Message.first,
        )
        for msg in messages:
            thread = threadmap[msg.mtid]
            if msg.first:
                msg.replies = thread["replies"]
                msg.subject = thread["subject"]
            else:
                msg.reply_to = thread["mid"]
            msg.sub = thread["sub"]
            msg.save()

        mailboxes = SubMessageMailbox.select()
        for mbox in mailboxes:
            mbox.mid = threadmap[mbox.mtid]["mid"]
            mbox.save()

        SubMessageLog.delete().where(
            SubMessageLog.action != SubMessageLogAction.CHANGE_MAILBOX
        ).execute()
        logs = SubMessageLog.select()
        for log in logs:
            log.mid = threadmap[log.mtid]["mid"]
            log.mailbox = int(log.desc)
            log.save()

    migrator.remove_fields("message", "thread", "first")
    migrator.remove_fields("sub_message_mailbox", "highlighted", "thread")
    migrator.remove_fields("sub_message_log", "action", "thread", "desc")
    migrator.add_not_null("sub_message_log", "mailbox")
    migrator.drop_index("sub_message_log", "updated")
    migrator.remove_model("message_thread")
