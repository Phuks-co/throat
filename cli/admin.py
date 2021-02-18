import click
from flask.cli import AppGroup
from peewee import fn
from app.models import User, UserMetadata

admin = AppGroup("admin", help="Manages admin users")


@admin.command(help="Grants admin privileges to an user")
@click.argument("username")
def add(username):
    try:
        user = User.get(fn.Lower(User.name) == username.lower())
    except User.DoesNotExist:
        print("Error: User does not exist")
        return
    UserMetadata.create(uid=user.uid, key="admin", value="1")
    print("Done.")


@admin.command(help="Removes admin privileges for an user")
@click.argument("username")
def remove(username):
    try:
        user = User.get(fn.Lower(User.name) == username.lower())
    except User.DoesNotExist:
        return print("Error: User does not exist.")

    try:
        umeta = UserMetadata.get(
            (UserMetadata.uid == user.uid) & (UserMetadata.key == "admin")
        )
        umeta.delete_instance()
        print("Done.")
    except UserMetadata.DoesNotExist:
        print("Error: User is not an administrator.")


@admin.command(name="list", help="List users with administrator privileges")
def list_admins():
    users = (
        User.select(User.name)
        .join(UserMetadata)
        .where((UserMetadata.key == "admin") & (UserMetadata.value == "1"))
    )
    print("Administrators: ")
    for i in users:
        print("  ", i.name)
