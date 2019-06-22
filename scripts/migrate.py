#!/usr/bin/env python3
import __fix
from peewee_migrate import Router
from playhouse.db_url import connect
import config
import os
import argparse

config.TESTING = False
database = connect(config.DATABASE_URL)
router = Router(database, migrate_dir='../app/migrations' if os.getcwd().endswith('scripts') else 'app/migrations')

parser = argparse.ArgumentParser(description='Apply or manage database migrations.')
parser.add_argument('-c', '--create', metavar='NAME', help='Creates a new migration')

args = parser.parse_args()

if args.create:
    router.create(args.create)
else:
    router.run()
