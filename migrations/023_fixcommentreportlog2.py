"""Peewee migrations -- 023_fixcommentreportlog2.py.

Part 2 of a 2 part migration.  See 022_fixcommentreportlog1.py.
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

    @migrator.create_model
    class CommentReportLog(pw.Model):
        rid = pw.ForeignKeyField(
            db_column="id", model=migrator.orm["sub_post_comment_report"], field="id"
        )
        action = pw.IntegerField(null=True)
        desc = pw.CharField(null=True)
        lid = pw.PrimaryKeyField()
        link = pw.CharField(null=True)
        time = pw.DateTimeField()
        uid = pw.ForeignKeyField(
            db_column="uid", null=True, model=migrator.orm["user"], field="uid"
        )
        target = pw.ForeignKeyField(
            db_column="target_uid", null=True, model=migrator.orm["user"], field="uid"
        )

        def __repr__(self):
            return f"<CommentReportLog action={self.action}>"

        class Meta:
            table_name = "comment_report_log"

    if not fake:
        CommentReportLogSave = migrator.orm["comment_report_log_save"]
        CommentReportLog.create_table(True)
        records = list(CommentReportLogSave.select().dicts())
        for r in records:
            r.pop("lid")
        CommentReportLog.insert_many(records).execute()

    migrator.remove_model("comment_report_log_save")


def rollback(migrator, database, fake=False, **kwargs):
    """Write your rollback migrations here."""
    # This migration and the previous one delete and recreate
    # CommentReportLog so a rollback is not necessary.
