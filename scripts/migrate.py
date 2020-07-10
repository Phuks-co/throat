#!/usr/bin/env python3
import __fix
from peewee_migrate import Router
from playhouse.db_url import connect
import os
import argparse
from app import create_app
from app.models import db as database

app = create_app()

router = Router(database, migrate_dir='../migrations' if os.getcwd().endswith('scripts') else 'migrations',
                ignore=['basemodel'])

parser = argparse.ArgumentParser(description='Apply or manage database migrations.')
parser.add_argument('-c', '--create', metavar='NAME', help='Creates a new migration')
parser.add_argument('-a', '--auto', metavar='NAME', help='Creates a new migration (automatic)')
parser.add_argument('-r', '--rollback', metavar='NAME', help='Rolls back a migration')

args = parser.parse_args()

if args.create:
    router.create(args.create)
elif args.auto:
    router.create(args.auto, 'app')
elif args.rollback:
    router.rollback(args.rollback)
else:
    router.run()
