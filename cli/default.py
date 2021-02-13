import click
from flask.cli import AppGroup
from peewee import fn
from app.models import Sub, SiteMetadata

default = AppGroup('default', help="""Manages default subs

Default subs are shown in the home page to logged out users, and newly registered users will be automatically
subscribed to these subs.

Adding or removing default subs has no impact on existing users.
""")


@default.command(help="Marks a sub as default")
@click.argument('sub')
def add(sub):
    try:
        sub = Sub.get(fn.Lower(Sub.name) == sub.lower())
    except Sub.DoesNotExist:
        return print("Error: Sub does not exist")

    try:
        SiteMetadata.get((SiteMetadata.key == 'default') & (SiteMetadata.value == sub.sid))
        print('Error: Sub is already a default!')
    except SiteMetadata.DoesNotExist:
        SiteMetadata.create(key='default', value=sub.sid)
        print('Done.')


@default.command(help="Removes a default sub")
@click.argument('sub')
def remove(sub):
    try:
        sub = Sub.get(fn.Lower(Sub.name) == sub.lower())
    except Sub.DoesNotExist:
        return print("Error: Sub does not exist")

    try:
        metadata = SiteMetadata.get((SiteMetadata.key == 'default') & (SiteMetadata.value == sub.sid))
        metadata.delete_instance()
        print('Done.')
    except SiteMetadata.DoesNotExist:
        print('Error: Sub is not a default')


@default.command(name="list", help="Lists all default subs")
def list_defaults():
    subs = SiteMetadata.select(Sub.name).join(Sub, on=Sub.sid == SiteMetadata.value).where(
        (SiteMetadata.key == 'default')).dicts()
    print("Default subs: ")
    for i in subs:
        print("  ", i['name'])
