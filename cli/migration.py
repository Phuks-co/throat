import logging
import click
from flask.cli import AppGroup
from peewee_migrate import Router
from app.models import dbp as database


migration = AppGroup("migration", help="Manages database migrations")


def get_router(migrate_dir):
    database.connect()
    logger = logging.getLogger("migration")
    logger.setLevel(logging.DEBUG)
    migrate_table = (
        "migratehistory" if migrate_dir == "migrations" else migrate_dir + "_history"
    )

    return Router(
        database,
        migrate_table=migrate_table,
        migrate_dir=migrate_dir,
        ignore=["basemodel"],
        logger=logger,
    )


def dirname_option(f):
    return click.option(
        "--dirname",
        default="migrations",
        help='Name of directory containing migrations (the default is "migrations")',
    )(f)


@migration.command(help="Applies all pending migrations")
@click.option(
    "--fake",
    default=False,
    is_flag=True,
    help="Marks the migrations as finished but does not run them",
)
@dirname_option
def apply(fake, dirname):
    router = get_router(dirname)
    router.run(fake=fake)


@migration.command(help="Applies migrations up to and including the named one ")
@click.argument("name")
@click.option(
    "--fake",
    default=False,
    is_flag=True,
    help="Marks the migrations as finished but does not run them",
)
@dirname_option
def apply_up_to(fake, dirname, name):
    router = get_router(dirname)
    router.run(name=name, fake=fake)


@migration.command(help="Rolls back a migration")
@click.argument("name")
@dirname_option
def rollback(name, dirname):
    router = get_router(dirname)
    router.rollback(name)


@migration.command(help="Creates a new migration")
@click.argument("name")
@dirname_option
def create(name, dirname):
    router = get_router(dirname)
    router.create(name, True)


@migration.command(name="list", help="Lists all migrations")
@dirname_option
def list_migrations(dirname):
    router = get_router(dirname)
    all_migrations = router.todo
    applied_migrations = router.done
    for m in all_migrations:
        sym = "✓" if m in applied_migrations else "✗"
        print(f"{sym} {m}")
