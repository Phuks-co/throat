import logging
import os
import tempfile
import pytest

from flask import current_app
from flask_login import current_user
from peewee_migrate import Router

from app import create_app, mail
from app.config import Config, config
from app.models import db, BaseModel, User, UserMetadata
from app.auth import auth_provider, email_validation_is_required

from test.utilities import csrf_token, pp


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

    yield app.test_client()

    if config.auth.provider != 'LOCAL':
        for user in User.select():
            try:
                auth_provider.actually_delete_user(user)
            except Exception as err:
                print(f"Error trying to clean up {user.name} in Keycloak realm:", err)
                raise err


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


def register_user(client, user_info):
    """Register a user with the client and leave them logged in."""
    rv = client.get('/')
    rv = client.post('/do/logout', data=dict(csrf_token=csrf_token(rv.data)),
                     follow_redirects=True)
    rv = client.get('/register')
    with mail.record_messages() as outbox:
        data = dict(csrf_token=csrf_token(rv.data),
                    username=user_info['username'],
                    password=user_info['password'],
                    confirm=user_info['password'],
                    invitecode='',
                    accept_tos=True,
                    captcha='xyzzy')
        if email_validation_is_required():
            data['email_required'] = user_info['email']
        else:
            data['email_optional'] = user_info['email']
        data.update(user_info)
        rv = client.post('/register',
                         data=data,
                         follow_redirects=True)

        if email_validation_is_required():
            message = outbox[-1]
            soup = BeautifulSoup(message.html, 'html.parser')
            token = soup.a['href'].split('/')[-1]
            rv = client.get("login/with-token/" + token,
                            follow_redirects=True)

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
