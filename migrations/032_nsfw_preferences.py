"""Peewee migrations -- 032_nsfw_preferences.py

Add admin site configuration options to control whether NSFW content
is shown to anonymous users, and to set the default initial
preferences for new users.

"""

import peewee as pw

SQL = pw.SQL


def migrate(migrator, database, fake=False, **kwargs):
    SiteMetadata = migrator.orm["site_metadata"]
    UserMetadata = migrator.orm["user_metadata"]
    if not fake:
        SiteMetadata.create(key="site.nsfw.anon.show", value="1")
        SiteMetadata.create(key="site.nsfw.anon.blur", value="1")
        SiteMetadata.create(key="site.nsfw.new_user_default.show", value="1")
        SiteMetadata.create(key="site.nsfw.new_user_default.blur", value="1")
        for um in UserMetadata.select().where(
            (UserMetadata.key == "nsfw") & (UserMetadata.value == "1")
        ):
            UserMetadata.create(uid=um.uid, key="nsfw_blur", value="1")


def rollback(migrator, database, fake=False, **kwargs):
    SiteMetadata = migrator.orm["site_metadata"]
    UserMetadata = migrator.orm["user_metadata"]
    if not fake:
        SiteMetadata.delete().where(
            SiteMetadata.key
            << [
                "site.nsfw.anon.show",
                "site.nsfw.anon.blur",
                "site.nsfw.new_user_default.show",
                "site.nsfw.new_user_default.blur",
            ]
        ).execute()
        UserMetadata.delete().where(UserMetadata.key == "nsfw_blur").execute()
