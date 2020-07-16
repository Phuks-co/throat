import logging
import os
import tempfile
import pytest

from peewee_migrate import Router

from app import create_app
from app.config import Config, config
from app.models import db, BaseModel, User, UserMetadata
from app.auth import auth_provider

from test.utilities import recursively_update


peewee_migrate_logger = logging.getLogger('peewee_migrate')
peewee_migrate_logger.setLevel(logging.WARNING)


@pytest.fixture
def test_config():
    """Extra configuration values to be used in a test."""
    return {}

# The fixture "client" is generated from this one by pytest-flask.
@pytest.fixture
def app(test_config):
    """Create the Flask app."""
    db_fd, db_name = tempfile.mkstemp()

    config_filename = os.environ.get('TEST_CONFIG', None)

    # Start with the defaults in config.py.
    config = Config(config_filename=config_filename,
                    use_environment=False)

    # Set some things that make sense for testing.
    # TODO set Redis database number to different than dev-server
    config['app']['testing'] = True
    config['app']['debug'] = False
    config['app']['development'] = False
    config['cache']['type'] = 'simple'
    config['database']['engine'] = 'SqliteDatabase'
    config['database']['name'] = db_name
    config['app']['languages'] = ['en']
    config['mail']['server'] = 'smtp.example.com'
    config['mail']['port'] = 8025
    config['mail']['default_from'] = 'test@example.com'

    recursively_update(config, test_config)

    app = create_app(config)

    app_context = app.app_context()
    app_context.push()

    # Might be faster to get this to work:
    # db.create_tables(BaseModel.__subclasses__())
    router = Router(db, migrate_dir='migrations', ignore=['basemodel'])
    router.run()

    yield app

    if config.auth.provider != 'LOCAL':
        for user in User.select():
            try:
                auth_provider.actually_delete_user(user)
            except Exception as err:
                print(f'Error trying to clean up {user.name} in Keycloak realm:', err)
                raise err


    app_context.pop()
    os.close(db_fd)
    os.unlink(db_name)


@pytest.fixture
def user_info():
    return dict(username='supertester',
                email='test@example.com',
                password='Safe123#$@lolnot')


@pytest.fixture
def user2_info():
    return dict(username='administrator',
                email='admin@example.com',
                password='999aaaAAA###')
