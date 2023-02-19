import logging
from mock import Mock
from peewee_migrate import Router

from app.models import dbp


def test_migrations(app_before_init_db):
    """The database migrations complete successfully."""
    app, conf_obj = app_before_init_db

    dbp.connect()

    if conf_obj.database.engine == "PostgresqlDatabase":
        dbp.execute_sql("DROP SCHEMA public CASCADE;")
        dbp.execute_sql("CREATE SCHEMA public;")
        dbp.execute_sql("GRANT ALL ON SCHEMA public TO public;")

    router = Router(dbp, migrate_dir="migrations", ignore=["basemodel"])
    router.run()

    applied_migrations = list(router.done)
    applied_migrations.reverse()

    # Shut up a warning in rollback that we can't do anything about.
    logging.getLogger("peewee_migrate").warn = Mock()

    # Make sure new rollbacks work.  The existing ones are what they are.
    for m in applied_migrations:
        if m == "029_message_read":
            break
        router.rollback()

    dbp.close()
