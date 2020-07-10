import os
import tempfile
import pytest

from peewee_migrate import Router

from app import create_app
from app.config import Config
from app.models import db

@pytest.fixture
def client():
    """Create the Flask test client."""
    db_fd, db_name = tempfile.mkstemp()

    config = Config()
    config['app']['testing'] = True
    config['app']['debug'] = False
    config['cache']['type'] = 'simple'
    config['database']['engine'] = 'SqliteDatabase'
    config['database']['name'] = db_name
    config['app']['languages'] = ['en']

    app = create_app(config)
    app_context = app.app_context()
    app_context.push()
    router = Router(db, migrate_dir='migrations', ignore=['basemodel'])
    router.run()

    yield app.test_client()

    app_context.pop()
    os.close(db_fd)
    os.unlink(db_name)

