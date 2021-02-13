import os
import sys
import logging
import click
from flask.cli import AppGroup
from peewee_migrate import Router
from app.models import dbp as database


migration = AppGroup('migration', help="Manages database migrations")


def get_router():
    database.connect()
    logger = logging.getLogger('migration')
    logger.setLevel(logging.DEBUG)

    return Router(database, migrate_dir='migrations', ignore=['basemodel'], logger=logger)


@migration.command(help="Applies all pending migrations")
@click.option('--fake', default=False, is_flag=True, help="Marks the migrations as finished but does not run them")
def apply(fake):
    router = get_router()
    router.run(fake=fake)


@migration.command(help="Rolls back a migration")
@click.argument('name')
def rollback(name):
    router = get_router()
    router.rollback(name)


@migration.command(help="Creates a new migration")
@click.argument('name')
def create(name):
    router = get_router()
    router.create(name, True)


@migration.command(name="list", help="Lists all migrations")
def list_admins():
    router = get_router()
    all_migrations = router.todo
    applied_migrations = router.done
    for m in all_migrations:
        sym = '✓' if m in applied_migrations else '✗'
        print(f"{sym} {m}")

