"""Peewee migrations -- 029_message_read.py

Remove an unused field from the Message model.

"""

import datetime as dt
from enum import IntEnum
import peewee as pw
from decimal import ROUND_HALF_EVEN

try:
    import playhouse.postgres_ext as pw_pext
except ImportError:
    pass

SQL = pw.SQL


def migrate(migrator, database, fake=False, **kwargs):
    """Write your migrations here."""
    migrator.remove_fields("message", "read")


def rollback(migrator, database, fake=False, **kwargs):
    """Write your rollback migrations here."""
    migrator.add_fields("message", read=pw.DateTimeField(null=True))
