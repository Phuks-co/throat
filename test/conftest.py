import bcrypt
from functools import lru_cache, wraps
import os
import pytest
from pyrsistent import freeze, thaw
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


def _make_config(config_dict) -> Config:
    """Create a standard testing Config from the given dictionary."""
    return Config(
        config_dict=config_dict,
        use_environment=False,
        model=SiteMetadata,
        cache=cache,
    )


def _freeze_dict_arg(func):
    """Freeze the argument of a function that takes a single dictionary.

    This decorator exists purely to get a hashable dictionary that can
    be cached with lru_cache, so func should be a function wrapped with
    the lru_cache decorator.
    """

    @wraps(func)
    def inner(arg: dict):
        return func(freeze(arg))

    return inner


@_freeze_dict_arg
@lru_cache()
def get_app(frozen_config_dict):
    """Create the Flask application, cached by config dictionary."""
    config = _make_config(thaw(frozen_config_dict))
    app = create_app(config)
    return app, config


@pytest.fixture
def app_before_init_db(test_config):
    """Create the Flask app with an uninitialized database."""
    db_name = ":memory:"

    config_filename = os.environ.get("TEST_CONFIG", None)
    if config_filename is None:
        custom_config = {}
    else:
        with open(config_filename) as stream:
            custom_config = yaml.safe_load(stream)

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

    config = {}
    recursively_update(config, test_defaults)
    recursively_update(config, custom_config)
    recursively_update(config, test_config)

    app, conf_obj = get_app(config)
    app_context = app.app_context()
    app_context.push()

    yield app, conf_obj

    app_context.pop()


# The fixture "client" is generated from this one by pytest-flask.
@pytest.fixture
def app(app_before_init_db):
    """Create the Flask app with an intialized database."""
    app, conf_obj = app_before_init_db
    cache.clear()

    if conf_obj.database.engine == "PostgresqlDatabase":
        db.execute_sql("DROP SCHEMA public CASCADE;")
        db.execute_sql("CREATE SCHEMA public;")
        db.execute_sql("GRANT ALL ON SCHEMA public TO public;")

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

    if conf_obj.database.engine == "Sqlitedatabase":
        db.detach(conf_obj.database.name)


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


@pytest.fixture
def user3_info():
    return dict(
        username="moderator", email="moderator@example.com", password="999aaaJJJ###"
    )
