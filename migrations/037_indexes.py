"""Peewee migrations -- 037_indexes.py."""

import datetime as dt
import peewee as pw
from decimal import ROUND_HALF_EVEN

try:
    import playhouse.postgres_ext as pw_pext
except ImportError:
    pass

SQL = pw.SQL


def migrate(migrator, database, fake=False, **kwargs):
    """Peewee can generate indexes for functions, but this functionality
    is not included in the migrator API."""
    User = migrator.orm["user"]
    ctx = database.get_sql_context()
    idx = pw.Index("user_name_lower", "user", [pw.fn.Lower(User.name)], unique=True)
    migrator.sql("".join(ctx.sql(idx)._sql))

    Sub = migrator.orm["sub"]
    ctx = database.get_sql_context()
    idx = pw.Index("sub_name_lower", "sub", [pw.fn.Lower(Sub.name)], unique=True)
    migrator.sql("".join(ctx.sql(idx)._sql))

    migrator.add_index("message", "posted", unique=False)
    migrator.add_index("sub_post", "link", unique=False)
    migrator.add_index("sub_post", "posted", unique=False)
    migrator.add_index("sub_post_comment", "time", unique=False)
    migrator.add_index("sub_post_comment_report", "datetime", unique=False)
    migrator.add_index("sub_post_comment_vote", "datetime", unique=False)
    migrator.add_index("sub_post_report", "datetime", unique=False)
    migrator.add_index("sub_post_vote", "datetime", unique=False)
    migrator.add_index("user_content_block", "target", unique=False)
    migrator.add_index("user_message_block", "target", unique=False)


def rollback(migrator, database, fake=False, **kwargs):
    """Write your rollback migrations here."""
    migrator.sql('DROP INDEX IF EXISTS "user_name_lower"')
    migrator.sql('DROP INDEX IF EXISTS "sub_name_lower"')

    migrator.drop_index("message", "posted")
    migrator.drop_index("sub_post", "link")
    migrator.drop_index("sub_post", "posted")
    migrator.drop_index("sub_post_comment", "time")
    migrator.drop_index("sub_post_comment_report", "datetime")
    migrator.drop_index("sub_post_comment_vote", "datetime")
    migrator.drop_index("sub_post_report", "datetime")
    migrator.drop_index("sub_post_vote", "datetime")
    migrator.drop_index("user_content_block", "target")
    migrator.drop_index("user_message_block", "target")
