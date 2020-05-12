#! /usr/bin/env python

import __fix
import argparse

from peewee import fn
from app.models import Sub, SiteMetadata

# Args
parser = argparse.ArgumentParser(description='Manage default subs.')
parser.add_argument('subname', help='name of the sub you want to work with')
addremove = parser.add_mutually_exclusive_group()
addremove.add_argument('-a', '--add', action='store_true', help='add a sub to defaults')
addremove.add_argument('-r', '--remove', action='store_true', help='remove a sub from defaults')
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


# Main
if args.add:
    addSub(args.subname)
elif args.remove:
    remSub(args.subname)
else:
    print('ERROR: No action specified. Try \"-h\" for help.')
