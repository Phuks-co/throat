"""Peewee migrations -- 035_user_block.py

Replace the UserIgnores model with the UserContentBlock and
UserMessageBlock models to give users more options for blocking
other users.

"""
import datetime
import peewee as pw

SQL = pw.SQL


def migrate(migrator, database, fake=False, **kwargs):
    """Write your migrations here."""
    User = migrator.orm["user"]

    @migrator.create_model
    class UserMessageBlock(pw.Model):
        uid = pw.ForeignKeyField(
            backref="usermessageblock_set",
            column_name="uid",
            field="uid",
            model=migrator.orm["user"],
        )
        target = pw.CharField(max_length=40)
        date = pw.DateTimeField()

        class Meta:
            table_name = "user_message_block"

    @migrator.create_model
    class UserContentBlock(pw.Model):
        uid = pw.ForeignKeyField(
            backref="usercontentblock_set",
            column_name="uid",
            field="uid",
            model=migrator.orm["user"],
        )
        target = pw.CharField(max_length=40)
        date = pw.DateTimeField()
        method = pw.IntegerField()  # 0=hide, 1=blur

        class Meta:
            table_name = "user_content_block"

    UserIgnores = migrator.orm["user_ignores"]

    if not fake:
        migrator.run()
        UserMetadata = migrator.orm["user_metadata"]
        TargetUserMetadata = UserMetadata.alias()
        ignores_except_admin = (
            UserIgnores.select()
            .join(
                UserMetadata,
                pw.JOIN.LEFT_OUTER,
                on=(
                    (UserMetadata.uid == UserIgnores.uid)
                    & (UserMetadata.key == "admin")
                ),
            )
            .join(
                TargetUserMetadata,
                pw.JOIN.LEFT_OUTER,
                on=(
                    (TargetUserMetadata.uid == UserIgnores.target)
                    & (TargetUserMetadata.key == "admin")
                ),
            )
            .where(
                (UserMetadata.value.is_null() | (UserMetadata.value == "0"))
                & (
                    TargetUserMetadata.value.is_null()
                    | (TargetUserMetadata.value == "0")
                )
            )
        )
        for ig in ignores_except_admin:
            UserMessageBlock.create(
                uid=ig.uid,
                target=ig.target,
                date=ig.date,
            )

    migrator.remove_model(UserIgnores, cascade=True)


def rollback(migrator, database, fake=False, **kwargs):
    """Write your rollback migrations here."""

    @migrator.create_model
    class UserIgnores(pw.Model):
        id = pw.AutoField()
        uid = pw.ForeignKeyField(
            backref="userignores_set",
            column_name="uid",
            field="uid",
            model=migrator.orm["user"],
        )
        target = pw.CharField(max_length=40)
        date = pw.DateTimeField()

        class Meta:
            table_name = "user_ignores"

    UserMessageBlock = migrator.orm["user_message_block"]
    UserContentBlock = migrator.orm["user_content_block"]

    if not fake:
        migrator.run()
        UserMetadata = migrator.orm["user_metadata"]
        for ig in UserMessageBlock.select():
            UserIgnores.create(uid=ig.uid, target=ig.target, date=ig.date)

    migrator.remove_model(UserMessageBlock, cascade=True)
    migrator.remove_model(UserContentBlock, cascade=True)
