""" Config manager """
import os
import yaml


cfg_defaults = { # key => default value
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
            "enable_chat": True,

            "changelog_sub": None,
            "btc_address": None,
            "xmr_address": None,

            "title_edit_timeout": 300,

            "sub_creation_min_level": 2,
            "sub_creation_admin_only": False,
            "sub_ownership_limit": 20,

            "daily_sub_posting_limit": 10,
            "daily_site_posting_limit": 25,
        },
        "cache": {
            "type": "null"
        },
        "sendgrid": {
            "api_key": '',
            "default_from": 'noreply@shitposting.space',
        },
        "storage": {
            "thumbnails":{
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
            "testing": True,
            "wtf_csrf_time_limit": None,
            "max_content_length": 10485760,  # 10mb
            "fallback_language": "en"
        },
    "database": {}
    }


class Map(dict):
    """ A dictionary object whose keys are accessable as attributes. """
    def __init__(self, sdict, defaults, prefix=''):
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
                self[key] = Map(self.get(key, {}), val, f'{self.prefix}{key}')
            elif key not in self.keys():
                self[key] = val;

        # Look for environment variables that override values or add additional values.
        if self.prefix != '':
            for var in os.environ.keys():
                if var.startswith(self.prefix):
                    self[var[len(self.prefix):].lower()] = os.environ.get(var)

    def __getattr__(self, attr):
        return self[attr]


class Config(Map):
    """ Main config object """
    def __init__(self):
        with open('config.yaml','r') as stream:
            self._cfg = yaml.safe_load(stream)

        super(Config, self).__init__(self._cfg, cfg_defaults)

    def get_flask_dict(self):
        flattened = {}
        for cpk in ['cache', 'sendgrid', 'app']:
            for i in self[cpk]:
                if cpk == 'app':
                    key = i.upper()
                else:
                    key = '{}_{}'.format(cpk, i).upper()
                flattened[key] = self[cpk][i]
        return flattened

config = Config()
