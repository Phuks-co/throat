"""Peewee migrations -- 036_modmail.py.

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
from enum import IntEnum
import peewee as pw

try:
    import playhouse.postgres_ext as pw_pext
except ImportError:
    pass

SQL = pw.SQL


class MessageMailbox(IntEnum):
    """Mailboxes for private messages."""

    INBOX = 200
    SENT = 201
    SAVED = 202
    ARCHIVED = 203  # Modmail only.
    TRASH = 204
    DELETED = 205


def migrate(migrator, database, fake=False, **kwargs):
    """Write your migrations here."""
    Message = migrator.orm["message"]
    User = migrator.orm["user"]
    SiteMetadata = migrator.orm["site_metadata"]

    @migrator.create_model
    class SubMessageMailbox(pw.Model):
        mid = pw.ForeignKeyField(db_column="mid", model=Message, field="mid")
        mailbox = pw.IntegerField(default=MessageMailbox.INBOX)

        class Meta:
            table_name = "sub_message_mailbox"

    @migrator.create_model
    class SubMessageLog(pw.Model):
        mid = pw.ForeignKeyField(db_column="mid", model=Message, field="mid")
        uid = pw.ForeignKeyField(db_column="uid", model=User, field="uid")
        mailbox = pw.IntegerField()
        updated = pw.DateTimeField(default=dt.datetime.now)

        class Meta:
            table_name = "sub_message_log"

    if not fake:
        try:
            SiteMetadata.get(SiteMetadata.key == "site.enable_modmail")
        except SiteMetadata.DoesNotExist:
            SiteMetadata.create(key="site.enable_modmail", value="0")


def rollback(migrator, database, fake=False, **kwargs):
    """Write your rollback migrations here."""
    migrator.remove_model("sub_message_mailbox")
    migrator.remove_model("sub_message_log")

    if not fake:
        SiteMetadata = migrator.orm["site_metadata"]
        SiteMetadata.delete().where(SiteMetadata.key == "site.enable_modmail").execute()
