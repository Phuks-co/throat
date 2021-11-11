"""Peewee migrations -- 040_vote_config

Add admin site configuration options to control whether users can
upvote their own posts and comments.
"""

import peewee as pw

SQL = pw.SQL


def migrate(migrator, database, fake=False, **kwargs):
    SiteMetadata = migrator.orm["site_metadata"]
    if not fake:
        SiteMetadata.create(key="site.self_voting.posts", value="1")
        SiteMetadata.create(key="site.self_voting.comments", value="0")


def rollback(migrator, database, fake=False, **kwargs):
    SiteMetadata = migrator.orm["site_metadata"]
    if not fake:
        SiteMetadata.delete().where(
            (SiteMetadata.key == "site.self_voting.posts")
            | (SiteMetadata.key == "site.self_voting.comments")
        ).execute()
