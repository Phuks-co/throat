"""Peewee migrations -- 022_fixcommentreportlog1.py.

Migration 014_createreportlogs.py erroneously created the
comment_report_log table with a foreign key constraint linked to
sub_post_report instead of sub_post_comment_report.  Fix that by
deleting and recreating the table.  This needs to be done in two
migrations because the new table cannot be created until the old one
is fully deleted, which happens after the migrate function is run.

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
    class CommentReportLogSave(pw.Model):
        rid = pw.ForeignKeyField(db_column='id', model=migrator.orm['sub_post_comment_report'], field='id')
        action = pw.IntegerField(null=True)
        desc = pw.CharField(null=True)
        lid = pw.PrimaryKeyField()
        link = pw.CharField(null=True)
        time = pw.DateTimeField()
        uid = pw.ForeignKeyField(db_column='uid', null=True, model=migrator.orm['user'], field='uid')
        target = pw.ForeignKeyField(db_column='target_uid', null=True, model=migrator.orm['user'], field='uid')

        def __repr__(self):
            return f'<CommentReportLogSave action={self.action}>'

        class Meta:
            table_name = 'comment_report_log_save'

    if not fake:
        CommentReportLog = migrator.orm['comment_report_log']
        SubPostCommentReport = migrator.orm['sub_post_comment_report']
        CommentReportLogSave.create_table(True)
        valid_ids = list((rep.id for rep in SubPostCommentReport.select()))
        records = list(CommentReportLog.select().
                       where(CommentReportLog.rid << valid_ids).dicts())
        for r in records:
            r.pop("lid")
        CommentReportLogSave.insert_many(records).execute()

    migrator.remove_model("comment_report_log")


def rollback(migrator, database, fake=False, **kwargs):
    """Write your rollback migrations here."""
    # This migration and the next one delete and recreate
    # CommentReportLog so a rollback is not necessary.
