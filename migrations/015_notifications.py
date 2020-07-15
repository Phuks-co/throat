"""Peewee migrations -- 015_notifications.py.

Some examples (model - class or model name)::

    > Model = migrator.orm['model_name']            # Return model in current state by name

    > migrator.sql(sql)                             # Run custom SQL
    > migrator.python(func, *args, **kwargs)        # Run python code
    > migrator.create_model(Model)                  # Create a model (could be used as decorator)
    > migrator.remove_model(model, cascade=True)    # Remove a model
    > migrator.add_fields(model, **fields)          # Add fields to a model
    > migrator.change_fields(model, **fields)       # Change fields
    > migrator.remove_fields(model, *field_names, cascade=True)
    > migrator.rename_field(model, old_field_name, new_field_name)
    > migrator.rename_table(model, new_table_name)
    > migrator.add_index(model, *col_names, unique=False)
    > migrator.drop_index(model, *col_names)
    > migrator.add_not_null(model, *field_names)
    > migrator.drop_not_null(model, *field_names)
    > migrator.add_default(model, field_name, default)

"""

import datetime as dt
import peewee as pw
from decimal import ROUND_HALF_EVEN

try:
    import playhouse.postgres_ext as pw_pext
except ImportError:
    pass

SQL = pw.SQL


def migrate(migrator, database, fake=False, **kwargs):
    """Write your migrations here."""

    class Notification(pw.Model):
        id = pw.AutoField()
        type = pw.CharField(max_length=255)
        sub = pw.ForeignKeyField(backref='notification_set', column_name='sid', field='sid', model=migrator.orm['sub'], null=True)
        post = pw.ForeignKeyField(backref='notification_set', column_name='pid', field='pid', model=migrator.orm['sub_post'], null=True)
        comment = pw.ForeignKeyField(backref='notification_set', column_name='cid', field='cid', model=migrator.orm['sub_post_comment'], null=True)
        sender = pw.ForeignKeyField(backref='notification_set', column_name='sentby', field='uid', model=migrator.orm['user'], null=True)
        target = pw.ForeignKeyField(backref='notification_set', column_name='receivedby', field='uid', model=migrator.orm['user'], null=True)
        read = pw.DateTimeField(null=True)
        content = pw.TextField(null=True)
        created = pw.DateTimeField()

        class Meta:
            table_name = "notification"

    Notification._meta.database = migrator.database
    Notification.create_table(True)

    # Migrate notifications out of the messages table
    Message = migrator.orm['message']
    SubPostComment = migrator.orm['sub_post_comment']
    SubPost = migrator.orm['sub_post']
    Sub = migrator.orm['sub']

    total = Message.select().where(Message.mtype << (4, 5)).count()
    print(" - Migrating replies", end='', flush=True)
    progress = 0
    inserts = []
    qry = Message.select(Message.mlink, Message.mtype, Message.receivedby, Message.read, Message.posted, SubPostComment.cid, SubPost.pid, SubPost.sid, SubPostComment.uid).join(SubPostComment, on=SubPostComment.cid == Message.mlink).join(SubPost).where(Message.mtype << (4, 5))
    for msg in qry.dicts():
        progress += 1
        print(f"\r - Migrating replies {progress}/{total}", end='', flush=True)
        # Here mlink is the comment's cid
        # comnt = SubPostComment.get(SubPostComment.cid == msg.mlink)
        # post = SubPost.get(SubPost.pid == comnt.pid)
        inserts.append({
            'type': 'POST_REPLY' if msg['mtype'] == 4 else 'COMMENT_REPLY',
            'sub': msg['sid'],
            'post': msg['pid'],
            'comment': msg['cid'],
            'sender': msg['uid'],
            'target': msg['receivedby'],
            'read': msg['read'],
            'created': msg['posted']
        })

    Notification.insert_many(inserts).execute()
    inserts = []
    print(" OK")

    total = Message.select().where(Message.mtype == 8).count()
    progress = 0
    print(f" - Migrating mentions 0/{total}", end='')
    for msg in Message.select().where(Message.mtype == 8):
        progress += 1
        print(f"\r - Migrating mentions {progress}/{total}", end='', flush=True)
        parts = msg.mlink.split("/")
        comnt = None
        if len(parts) == 5:  # We guess if it's a comment or a post based on the permalink -_-
            mtype = 'COMMENT_MENTION'
            comnt = SubPostComment.get(SubPostComment.cid == parts[-1])
        else:
            mtype = 'POST_MENTION'
        post = SubPost.get(SubPost.pid == parts[3])

        inserts.append({
            'type': mtype,
            'sub': post.sid,
            'post': post.pid,
            'comment': comnt.cid if comnt else None,
            'sender': comnt.uid if comnt else post.uid,
            'target': msg.receivedby,
            'read': msg.read,
            'created': msg.posted
        })
    print(" OK")
    Notification.insert_many(inserts).execute()
    inserts = []

    total = Message.select().where(Message.mtype << (2, 7, 11)).count()
    progress = 0
    print(f" - Migrating modmail 0/{total}", end='')
    for msg in Message.select().where(Message.mtype << (2, 7, 11)):
        progress += 1
        print(f"\r - Migrating modmail {progress}/{total}", end='', flush=True)
        # Link is sub name
        try:
            sub = Sub.get(pw.fn.Lower(Sub.name) == msg.mlink.lower())
        except Sub.DoesNotExist:
            # Some really really legacy situation here...
            continue
        if msg.mtype == 2:
            mtype = 'MOD_INVITE' + ('_JANITOR' if "janitor" in msg.content else "")
            msg.content = None
        elif msg.mtype == 7:
            if 'unbanned' in msg.subject:
                mtype = 'SUB_UNBAN'
            else:
                mtype = 'SUB_BAN'
        else:
            mtype = 'POST_DELETE'
        inserts.append({
            'type': mtype,
            'sub': sub.sid,
            'post': None,
            'comment': None,
            'sender': msg.sentby,
            'target': msg.receivedby,
            'read': msg.read,
            'created': msg.posted,
            'content': msg.content
        })
    print(" OK")
    print("Dumping everything into the db...")

    Notification.insert_many(inserts).execute()


def rollback(migrator, database, fake=False, **kwargs):
    """Write your rollback migrations here."""

    migrator.remove_model('notification')
