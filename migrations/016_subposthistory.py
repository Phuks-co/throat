"""Peewee migrations -- 016_SubPostContentHistory.py.
"""

import datetime as dt
import peewee as pw

SQL = pw.SQL


def migrate(migrator, database, fake=False, **kwargs):
    """Write your migrations here."""

    @migrator.create_model
    class SubPostContentHistory(pw.Model):
        pid = pw.ForeignKeyField(backref='SubPostContentHistory_set', column_name='pid', field='pid', model=migrator.orm['sub_post'], null=True)
        content = pw.CharField(max_length=255, null=True)
        datetime = pw.DateTimeField()

        class Meta:
            table_name = "sub_post_content_history"

    @migrator.create_model
    class SubPostTitleHistory(pw.Model):
        pid = pw.ForeignKeyField(backref='SubPostTitleHistory', column_name='pid', field='pid', model=migrator.orm['sub_post'], null=True)
        title = pw.CharField(max_length=255, null=True)
        datetime = pw.DateTimeField()

        class Meta:
            table_name = "sub_post_title_history"


def rollback(migrator, database, fake=False, **kwargs):
    """Write your rollback migrations here."""
    migrator.remove_model('SubPostContentHistory')
    migrator.remove_model('SubPostTitleHistory')
