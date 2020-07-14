"""Peewee migrations -- 014_createreportlogs.py.
"""

import datetime as dt
import peewee as pw

SQL = pw.SQL


def migrate(migrator, database, fake=False, **kwargs):
    """Write your migrations here."""

    @migrator.create_model
    class PostReportLog(pw.Model):
        rid = pw.ForeignKeyField(db_column='id', model=migrator.orm['sub_post_report'], field='id')
        action = pw.IntegerField(null=True)
        desc = pw.CharField(null=True)
        lid = pw.PrimaryKeyField()
        link = pw.CharField(null=True)
        time = pw.DateTimeField()
        uid = pw.ForeignKeyField(db_column='uid', null=True, model=migrator.orm['user'], field='uid')
        target = pw.ForeignKeyField(db_column='target_uid', null=True, model=migrator.orm['user'], field='uid')

        def __repr__(self):
            return f'<CommentReportLog action={self.action}>'

        class Meta:
            table_name = 'comment_report_log'


    @migrator.create_model
    class CommentReportLog(pw.Model):
        rid = pw.ForeignKeyField(db_column='id', model=migrator.orm['sub_post_comment_report'], field='id')
        action = pw.IntegerField(null=True)
        desc = pw.CharField(null=True)
        lid = pw.PrimaryKeyField()
        link = pw.CharField(null=True)
        time = pw.DateTimeField()
        uid = pw.ForeignKeyField(db_column='uid', null=True, model=migrator.orm['user'], field='uid')
        target = pw.ForeignKeyField(db_column='target_uid', null=True, model=migrator.orm['user'], field='uid')

        def __repr__(self):
            return f'<CommentReportLog action={self.action}>'

        class Meta:
            table_name = 'comment_report_log'
