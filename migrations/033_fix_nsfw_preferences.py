"""Peewee migrations -- 033_fix_nsfw_preferences.py

The migration in 032_nsfw_preferences.py set the nsfw_blur
user preference for all users who had the nsfw preference set.
Turn nsfw_blur off for all users.
"""

import peewee as pw

SQL = pw.SQL


def migrate(migrator, database, fake=False, **kwargs):
    UserMetadata = migrator.orm["user_metadata"]
    if not fake:
        UserMetadata.delete().where(UserMetadata.key == "nsfw_blur").execute()


def rollback(migrator, database, fake=False, **kwargs):
    pass
