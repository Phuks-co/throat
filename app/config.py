""" Config manager """
import os
import yaml
from flask import current_app
from werkzeug.local import LocalProxy
import logging


cfg_defaults = {  # key => default value
        "site": {
            "name": 'Throat',
            "lema": 'Throat: Open discussion ;D',
            "copyright": "Umbrella Corp",
            "enable_totp": False,
            "placeholder_account": "Site",
            "sub_prefix": 's',
            "enable_security_question": False,
            "cas_authorized_hosts": [],
            "allow_uploads": False,
            "allow_video_uploads": True,
            "upload_max_size": 16777216,
            "upload_min_level": 0,
            "enable_chat": True,
            "sitelog_public": True,
            "force_sublog_public": True,

            "changelog_sub": None,
            "btc_address": None,
            "xmr_address": None,

            "title_edit_timeout": 300,

            "sub_creation_min_level": 2,
            "sub_creation_admin_only": False,
            "sub_ownership_limit": 20,
            "edit_history": False,

            "daily_sub_posting_limit": 10,
            "daily_site_posting_limit": 25,

            # Removing things from this list will work but adding will not.
            # See Expando.js.
            "expando_sites": ['hooktube.com', 'www.hooktube.com', 'youtube.com',
                              'www.youtube.com', 'youtu.be', 'gfycat.com',
                              'streamja.com', 'streamable.com', 'vimeo.com',
                              'vine.co', 'instaud.io'],

            "footer": {
                "links": {
                    "ToS": "/wiki/tos",
                    "Privacy": "/wiki/privacy"
                }
            },

            "archive_post_after": 60
        },
        "auth": {
            "provider": 'LOCAL',
            "require_valid_emails": False,
            "keycloak": {}
        },
        "cache": {
            "type": "null"
        },
        "mail": {},
        "storage": {
            "provider": 'LOCAL',
            "acl": "private",
            "server": False,
            "server_url": '/files/',
            "thumbnails": {
                "path": './thumbs',
                "url": 'https://thumbnails.shitposting.space/',
            },
            "uploads": {
                "path": './stor',
                "url": 'https://useruploads.shitposting.space/',
            }
        },
        "app": {
            "redis_url": 'redis://127.0.0.1:6379',
            "secret_key": 'yS\x1c\x88\xd7\xb5\xb0\xdc\t:kO\r\xf0D{"Y\x1f\xbc^\xad',
            "debug": True,
            "development": False,
            "wtf_csrf_time_limit": None,
            "max_content_length": 10485760,  # 10mb
            "fallback_language": "en",
            "testing": False
        },
        "aws": {},
        "database": {}
    }


class Map(dict):
    """ A dictionary object whose keys are accessable as attributes. """
    def __init__(self, sdict, defaults, use_environment=True, prefix=''):
        """Create a Map from the dictionary sdict, with missing values filled
        in from defaults. If a non-empty prefix string is supplied,
        and any environment variables exist beginning with that
        prefix, add those values to the dictionary overwriting
        anything in sdict or default.
        """
        super(Map, self).__init__(dict(sdict))
        self.prefix = ('' if prefix == '' else prefix + '_').upper()

        # If any values are missing, copy them from defaults.
        # Turn all subdictionaries into Maps as well.
        for key, val in defaults.items():
            if isinstance(val, dict):
                self[key] = Map(self.get(key, {}), val, use_environment,
                                f'{self.prefix}{key}')
            elif key not in self.keys():
                self[key] = val

       # Look for environment variables that override values or add additional values.
        if self.prefix != '' and use_environment:
            for var in os.environ.keys():
                if var.startswith(self.prefix):
                    self[var[len(self.prefix):].lower()] = os.environ.get(var)

    def __getattr__(self, attr):
        return self[attr]


class Config(Map):
    """ Main config object """
    def __init__(self, config_filename=None, use_environment=True):
        if config_filename is None:
            cfg = {}
        else:
            with open(config_filename, 'r') as stream:
                cfg = yaml.safe_load(stream)

        super(Config, self).__init__(cfg, cfg_defaults, use_environment=use_environment)
        self.check_storage_config()
        self.check_auth_config()

    def check_storage_config(self):
        """Adjust our storage config for compatibility with flask-cloudy."""
        storage = self.storage
        if storage.provider == 'LOCAL':
            # Make sure our storage paths are absolute.
            storage.thumbnails['path'] = os.path.abspath(storage.thumbnails['path'])
            storage.uploads['path'] = os.path.abspath(storage.uploads['path'])
            storage['container'] = storage.uploads['path']
            if storage.server:
                if storage.uploads.path != storage.thumbnails.path:
                    logging.warning("Thumbnails will not be served by local server "
                                    "because thumbnails and uploads paths differ")
                if storage['server_url'][-1] == '/':
                    # flask-cloudy does not want the trailing slash
                    self.storage['server_url'] = self.storage['server_url'][:-1]

        storage.acl = '' if storage.acl is None else storage.acl

        # This is not for flask-cloudy, just to make config more human-friendly
        ensure_trailing_slash(storage.thumbnails, 'url')
        ensure_trailing_slash(storage.uploads, 'url')

    def check_auth_config(self):
        ensure_trailing_slash(self.auth.keycloak, 'server')

    def get_flask_dict(self):
        flattened = {}
        for cpk in ['cache', 'mail', 'sendgrid', 'app']:
            if cpk in self.keys():
                for i in self[cpk]:
                    if cpk == 'app':
                        key = i.upper()
                    else:
                        key = '{}_{}'.format(cpk, i).upper()
                    flattened[key] = self[cpk][i]

        # These values are used by flask-cloudy.
        for key in ['provider', 'key', 'secret', 'container', 'server', 'server_url']:
            if key in self.storage:
                flattened[f'STORAGE_{key}'.upper()] = self.storage[key]
        return flattened


def ensure_trailing_slash(d, key):
    """ Add a slash to the end of a dictionary entry if it doesn't already have one. """
    if key in d and d[key] and d[key][-1] != '/':
        d[key] = d[key] + '/'


config = LocalProxy(lambda: current_app.config['THROAT_CONFIG'])
