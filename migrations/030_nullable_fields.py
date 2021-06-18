"""Peewee migrations -- 030_nullable fields.py.

Add not-null constraints to columns on the sub and sub_post tables
that in practice cannot be null as they cause obvious application
errors by violating implicit assumptions.

Because these failures are so obvious this migration does not include
a data migration, only the schema change.
"""

import peewee as pw

SQL = pw.SQL


def migrate(migrator, database, fake=False, **kwargs):
    migrator.add_not_null("sub", "name")

    migrator.add_not_null("sub_post", "deleted")
    migrator.add_not_null("sub_post", "posted")
    migrator.add_not_null("sub_post", "score")
    migrator.add_not_null("sub_post", "sid")
    migrator.add_not_null("sub_post", "title")
    migrator.add_not_null("sub_post", "uid")


def rollback(migrator, database, fake=False, **kwargs):
    migrator.drop_not_null("sub", "name")

    migrator.drop_not_null("sub_post", "deleted")
    migrator.drop_not_null("sub_post", "posted")
    migrator.drop_not_null("sub_post", "score")
    migrator.drop_not_null("sub_post", "sid")
    migrator.drop_not_null("sub_post", "title")
    migrator.drop_not_null("sub_post", "uid")
