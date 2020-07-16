#! /usr/bin/env python

import __fix
import argparse

from peewee import fn
from app.models import Sub, SiteMetadata
from app import create_app

app = create_app()

# Args
parser = argparse.ArgumentParser(description='Manage default subs.')

addremove = parser.add_mutually_exclusive_group()
addremove.add_argument('-a', '--add', metavar='SUBNAME', help='add a sub to defaults')
addremove.add_argument('-r', '--remove', metavar='SUBNAME', help='remove a sub from defaults')
addremove.add_argument('-l', '--list', action='store_true', help='List administrators')

args = parser.parse_args()


# Funcs
def getSid(subname):
    try:
        sub = Sub.get(fn.Lower(Sub.name) == subname.lower())
        return True, sub.sid
    except Sub.DoesNotExist:
        return False, ''


def addSub(subname):
    isSub, sid = getSid(subname)
    if isSub:
        try:
            metadata = SiteMetadata.get((SiteMetadata.key == 'default') & (SiteMetadata.value == sid))
            print('ERROR: Sub \"' + subname + '\" is already a default!')
        except SiteMetadata.DoesNotExist:
            SiteMetadata.create(key='default', value=sid)
            print('SUCCESS: Sub \"' + subname + '\" added to defaults.')
    else:
        print('ERROR: Sub \"' + subname + '\" does not exist!')


def remSub(subname):
    isSub, sid = getSid(subname)
    if isSub:
        try:
            metadata = SiteMetadata.get((SiteMetadata.key == 'default') & (SiteMetadata.value == sid))
            metadata.delete_instance()
            print('SUCCESS: Sub \"' + subname + '\" removed from defaults.')
        except SiteMetadata.DoesNotExist:
            print('ERROR: Sub \"' + subname + '\" is not a default!')
        except:
            print('ERROR: Unknown error.')
    else:
        print('ERROR: Sub \"' + subname + '\" does not exist!')


def listSubs():
    defaults = [x.value for x in SiteMetadata.select().where(SiteMetadata.key == 'default')]
    defaults = Sub.select(Sub.sid, Sub.name).where(Sub.sid << defaults)
    print("Default Subs: ")
    for i in defaults:
        print("  ", i.name)


# Main
if args.add:
    addSub(args.add.lower())
elif args.remove:
    remSub(args.remove.lower())
elif args.list:
    listSubs()
else:
    print('ERROR: No action specified. Try \"-h\" for help.')
