"""Peewee migrations -- 032_archive_sticky_posts

Add a admin site configuration option to control whether sticky
posts are archived in the same way as regular posts.
"""

import peewee as pw

SQL = pw.SQL


def migrate(migrator, database, fake=False, **kwargs):
    SiteMetadata = migrator.orm["site_metadata"]
    if not fake:
        SiteMetadata.create(key="site.archive_sticky_posts", value="1")


def rollback(migrator, database, fake=False, **kwargs):
    SiteMetadata = migrator.orm["site_metadata"]
    if not fake:
        SiteMetadata.delete().where(
            SiteMetadata.key == "site.archive_sticky_posts"
        ).execute()
