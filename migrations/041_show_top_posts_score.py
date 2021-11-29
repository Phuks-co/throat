"""Peewee migrations -- 041_show_top_posts_score

Add a admin site configuration option to control whether the scores
are shown with the top posts of the last 24 hours.

"""

import peewee as pw

SQL = pw.SQL


def migrate(migrator, database, fake=False, **kwargs):
    SiteMetadata = migrator.orm["site_metadata"]
    if not fake:
        SiteMetadata.create(key="site.top_posts.show_score", value="1")


def rollback(migrator, database, fake=False, **kwargs):
    SiteMetadata = migrator.orm["site_metadata"]
    if not fake:
        SiteMetadata.delete().where(
            SiteMetadata.key == "site.top_posts.show_score"
        ).execute()
