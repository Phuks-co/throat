import logging
import os
import tempfile
import pytest

from peewee_migrate import Router

from app import create_app
from app.config import Config
from app.models import db

peewee_migrate_logger = logging.getLogger("peewee_migrate")
peewee_migrate_logger.setLevel(logging.WARNING)

@pytest.fixture
def test_config():
    """Extra configuration values to be used in a test."""
    return {}


@pytest.fixture
def client(test_config):
    """Create the Flask test client."""
    db_fd, db_name = tempfile.mkstemp()

    # Start with the defaults in config.py.
    config = Config(use_environment=False)

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
    router = Router(db, migrate_dir='migrations', ignore=['basemodel'])
    router.run()

    yield app.test_client()

    app_context.pop()
    os.close(db_fd)
    os.unlink(db_name)


def recursively_update(dictionary, new_values):
    for elem in new_values.keys():
        if (elem in dictionary.keys() and
                isinstance(new_values[elem], dict) and
                isinstance(dictionary[elem], dict)):
            recursively_update(dictionary[elem], new_values[elem])
        else:
            dictionary[elem] = new_values[elem]
