"""Peewee migrations -- sub_flair_display_order.py.
Adds a new field to the sub_flair model to allow sub mods to choose the order.
"""

import peewee as pw

SQL = pw.SQL


def migrate(migrator, database, fake=False, **kwargs):
    """Write your migrations here."""
    migrator.add_fields(
        migrator.orm['sub_flair'],
        display_order=pw.IntegerField(constraints=[SQL("DEFAULT 1")]),
    )

def rollback(migrator, database, fake=False, **kwargs):
    """Write your rollback migrations here."""
    migrator.remove_fields(migrator.orm['sub_flair'], 'display_order')
