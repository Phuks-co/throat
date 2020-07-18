"""Peewee migrations -- 010_subrules.py.
"""

import datetime as dt
import peewee as pw

SQL = pw.SQL


def migrate(migrator, database, fake=False, **kwargs):
    """Write your migrations here."""

    @migrator.create_model
    class Subrule(pw.Model):
        rid = pw.PrimaryKeyField()
        sid = pw.ForeignKeyField(backref='subrule_set', column_name='sid', field='sid', model=migrator.orm['sub'], null=True)
        text = pw.CharField(max_length=255, null=True)

        class Meta:
            table_name = "sub_rule"
