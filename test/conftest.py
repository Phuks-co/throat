import bcrypt
import os
import tempfile
import pytest
import yaml

from app import create_app
from app.config import Config
from app.models import db, BaseModel, User, SiteMetadata
from app.caching import cache
from app.auth import auth_provider

from test.utilities import recursively_update, add_config_to_site_metadata


@pytest.fixture
def test_config():
    """Extra configuration values to be used in a test."""
    return {}


# The fixture "client" is generated from this one by pytest-flask.
@pytest.fixture
def app(test_config):
    """Create the Flask app."""
    db_fd, db_name = tempfile.mkstemp()

    config_filename = os.environ.get("TEST_CONFIG", None)
    if config_filename is None:
        config = {}
    else:
        with open(config_filename) as stream:
            config = yaml.safe_load(stream)

    # Set some things that make sense for testing.
    test_defaults = {
        "app": {
            "debug": False,
            "development": False,
            "languages": ["en"],
            "testing": True,
        },
        # TODO set Redis database number to different than dev-server and use Redis here.
        "cache": {"type": "simple"},
        "database": {"engine": "SqliteDatabase", "name": db_name},
        "mail": {
            "server": "smtp.example.com",
            "port": 8025,
            "default_from": "test@example.com",
        },
        "ratelimit": {"enabled": False},
    }

    recursively_update(config, test_defaults)
    recursively_update(config, test_config)

    conf_obj = Config(
        config_dict=config,
        use_environment=False,
        model=SiteMetadata,
        cache=cache,
    )
    app = create_app(conf_obj)
    app_context = app.app_context()
    app_context.push()
    cache.clear()
    db.create_tables(BaseModel.__subclasses__())
    add_config_to_site_metadata(conf_obj)

    yield app

    if conf_obj.auth.provider != "LOCAL":
        for user in User.select():
            try:
                auth_provider.actually_delete_user(user)
            except Exception as err:
                print(f"Error trying to clean up {user.name} in Keycloak realm:", err)
                raise err

    app_context.pop()
    os.close(db_fd)
    os.unlink(db_name)


@pytest.fixture(autouse=True)
def fast_hashing(monkeypatch):
    def just_add_salt(data, salt):
        assert isinstance(data, bytes)
        assert isinstance(salt, bytes)
        data = bytearray(data)
        data.append(salt[-1])
        return bytes(data)

    monkeypatch.setattr(bcrypt, "hashpw", just_add_salt)


@pytest.fixture
def user_info():
    return dict(
        username="supertester", email="test@example.com", password="Safe123#$@lolnot"
    )


@pytest.fixture
def user2_info():
    return dict(
        username="administrator", email="admin@example.com", password="999aaaAAA###"
    )
