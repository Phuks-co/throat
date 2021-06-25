"""Peewee migrations -- 031_notifications_on_icon

Add a admin site configuration option to control whether notifications are
shown graphically on the icon or textually in the page title.
"""

import peewee as pw

SQL = pw.SQL


def migrate(migrator, database, fake=False, **kwargs):
    SiteMetadata = migrator.orm["site_metadata"]
    if not fake:
        SiteMetadata.create(key="site.notifications_on_icon", value="1")


def rollback(migrator, database, fake=False, **kwargs):
    SiteMetadata = migrator.orm["site_metadata"]
    if not fake:
        SiteMetadata.delete().where(
            SiteMetadata.key == "site.notifications_on_icon"
        ).execute()
