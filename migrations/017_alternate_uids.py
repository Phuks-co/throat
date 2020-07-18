"""Peewee migrations -- 017_alternate_uids.py.
"""

import datetime as dt
import peewee as pw

SQL = pw.SQL


def migrate(migrator, database, fake=False, **kwargs):
    """Write your migrations here."""
    migrator.add_fields(migrator.orm['user'], alt_uid=pw.CharField(column_name='alt_uid', null=True, max_length=40))



def rollback(migrator, database, fake=False, **kwargs):
    """Write your rollback migrations here."""
    migrator.remove_fields(migrator.orm['user'], 'alt_uid')
