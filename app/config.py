""" Config manager """
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

            "changelog_sub": None,
            "btc_address": None,
            "xmr_address": None,

            "title_edit_timeout": 300
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
        }

    }


class Map(dict):
    def __init__(self, sdict, defaults):
        super(Map, self).__init__(sdict)
        self.defaults = defaults
        for k, v in sdict.items():
            self[k] = v

    def _get(self, attr):
        try:
            return self[attr]
        except KeyError:
            return self.defaults[attr]

    def __getattr__(self, attr):
        val = self._get(attr)
        if isinstance(val, dict):
            return Map(val, self.defaults.get(attr, {}))
        return val


class Config(Map):
    """ Main config object """
    def __init__(self):
        with open('config.yaml','r') as stream:
            self._cfg = yaml.safe_load(stream)
        
        super(Config, self).__init__(self._cfg, cfg_defaults)

    def get_flask_dict(self):
        flattened = {}
        for cpk in ['cache', 'sendgrid', 'app']:
            for i in self._cfg[cpk]:
                if cpk == 'app':
                    key = i.upper()
                else:
                    key = '{}_{}'.format(cpk, i).upper()
                flattened[key] = self._cfg[cpk][i]
        return flattened

config = Config()