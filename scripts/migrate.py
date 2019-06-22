#!/usr/bin/env python3
import __fix
from peewee_migrate import Router
from playhouse.db_url import connect
import config
config.TESTING = False
database = connect(config.DATABASE_URL)
router = Router(database, migrate_dir='../app/migrations')

router.run()
