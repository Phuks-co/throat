#!/usr/bin/env python3
import __fix
from peewee_migrate import Router
from playhouse.db_url import connect
import config
import os
import argparse

config.TESTING = False
database = connect(config.DATABASE_URL)
router = Router(database, migrate_dir='../migrations' if os.getcwd().endswith('scripts') else 'migrations',
                ignore=['basemodel'])

parser = argparse.ArgumentParser(description='Apply or manage database migrations.')
parser.add_argument('-c', '--create', metavar='NAME', help='Creates a new migration')
parser.add_argument('-a', '--auto', metavar='NAME', help='Creates a new migration (automatic)')

args = parser.parse_args()

if args.create:
    router.create(args.create)
elif args.auto:
    router.create(args.auto, 'app')
else:
    router.run()
