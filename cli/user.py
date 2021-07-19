import click
from flask.cli import AppGroup
from peewee import JOIN
from app.models import User, UserMetadata

user = AppGroup("user", help="Manage users")


@user.command(name="set-pref-all")
@click.option(
    "--name",
    type=click.Choice(["labrat", "nostyles", "nsfw", "nsfw_blur", "nochat"]),
    help="Name of the setting to modify",
    required=True,
)
@click.option(
    "--value",
    type=click.Choice(["0", "1"]),
    help="Use 0 to disable and 1 to enable",
    required=True,
)
def set_pref_all(name, value):
    """Set a user preference for all users.  This command will overwrite
    the existing settings of all users and cannot be undone, so use with care.
    """
    UserMetadata.delete().where(UserMetadata.key == name).execute()
    if value == "1":
        for user in User.select():
            UserMetadata.create(uid=user.uid, key=name, value="1")


@user.command(name="set-nsfw-hidden-to-blur")
def set_nsfw_hidden_to_blur():
    """Change the NSFW preference of all users who have show NSFW content off
    to "Blur until clicked".  This command will overwrite users' existing
    settings and cannot be undone, so use with care."""
    for user in (
        User.select()
        .join(UserMetadata, JOIN.LEFT_OUTER)
        .where(
            (UserMetadata.key == "nsfw")
            & (UserMetadata.value.is_null() | (UserMetadata.value == "0"))
        )
    ):
        UserMetadata.delete().where(
            (UserMetadata.uid == user.uid)
            & ((UserMetadata.key == "nsfw") | (UserMetadata.key == "nsfw_blur"))
        ).execute()
        UserMetadata.create(uid=user.uid, key="nsfw", value="1")
        UserMetadata.create(uid=user.uid, key="nsfw_blur", value="1")
