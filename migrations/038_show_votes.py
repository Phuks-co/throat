"""Peewee migrations -- 038_show_votes.

Add a admin site configuration option to control whether the counts of
upvotes and downvotes on a post or comment are visible to users.

"""

import peewee as pw

SQL = pw.SQL


def migrate(migrator, database, fake=False, **kwargs):
    SiteMetadata = migrator.orm["site_metadata"]
    if not fake:
        SiteMetadata.create(key="site.show_votes", value="1")


def rollback(migrator, database, fake=False, **kwargs):
    SiteMetadata = migrator.orm["site_metadata"]
    if not fake:
        SiteMetadata.delete().where(SiteMetadata.key == "site.show_votes").execute()
