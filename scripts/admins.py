#!/usr/bin/env python3
import __fix
import argparse
import sys

from peewee import fn
from app.models import User, Client, Grant, Message, SiteLog, SiteMetadata, Sub, \
    SubFlair, SubLog, SubMetadata, SubPost, SubPostComment, \
    SubPostCommentVote, SubPostMetadata, SubPostVote, SubStylesheet, \
    SubSubscriber, Token, UserMetadata, UserSaved, \
    UserUploads, UserIgnores, \
    SubUploads, SubPostPollOption, SubPostPollVote, SubPostReport, APIToken, APITokenSettings
from app import create_app

app = create_app()

parser = argparse.ArgumentParser(description='Manage administrators.')
addremove = parser.add_mutually_exclusive_group(required=True)
addremove.add_argument('--add', metavar='USERNAME', help='Make a user administrator')
addremove.add_argument('--remove', metavar='USERNAME', help='Remove admin privileges')
addremove.add_argument('-l', '--list', action='store_true', help='List administrators')

args = parser.parse_args()


if args.add:
    try:
        user = User.get(fn.Lower(User.name) == args.add.lower())
    except User.DoesNotExist:
        print("Error: User does not exist")
        sys.exit(1)
    UserMetadata.create(uid=user.uid, key='admin', value='1')
    print("Done.")
elif args.remove:
    try:
        user = User.get(fn.Lower(User.name) == args.remove.lower())
    except User.DoesNotExist:
        print("Error: User does not exist.")
        sys.exit(1)

    try:
        umeta = UserMetadata.get((UserMetadata.uid == user.uid) & (UserMetadata.key == 'admin'))
        umeta.delete_instance()
        print("Done.")
    except UserMetadata.DoesNotExist:
        print("Error: User is not an administrator.")
elif args.list:
    users = User.select(User.name).join(UserMetadata).where((UserMetadata.key == 'admin') & (UserMetadata.value == '1'))
    print("Administrators: ")
    for i in users:
        print("  ", i.name)
