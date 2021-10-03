""" Config manager """
import os
from pathlib import Path
import yaml
from flask import current_app
from flask_babel import lazy_gettext as _l
from werkzeug.local import LocalProxy
import logging


defaults = {  # key => default value
    "site": {
        "enable_totp": False,
        "sub_prefix": "s",
        "cas_authorized_hosts": [],
        "upload_max_size": 16777216,
        "btc_address": None,
        "xmr_address": None,
        # Removing things from this list will work but adding will not.
        # See Expando.js.
        "expando_sites": [
            "hooktube.com",
            "www.hooktube.com",
            "youtube.com",
            "www.youtube.com",
            "youtu.be",
            "gfycat.com",
            "streamja.com",
            "streamable.com",
            "vimeo.com",
            "vine.co",
            "instaud.io",
            "player.vimeo.com",
        ],
        "footer": {"links": {"ToS": "/wiki/tos", "Privacy": "/wiki/privacy"}},
        "trusted_proxy_count": 0,
        "custom_hot_sort": False,
        "icon_url": None,
        "logo": "app/static/img/throat-logo.svg",
    },
    "auth": {"provider": "LOCAL", "require_valid_emails": False, "keycloak": {}},
    "cache": {"type": "null"},
    "mail": {},
    "storage": {
        "provider": "LOCAL",
        "endpoint_url": None,
        "acl": "private",
        "server": False,
        "server_url": "/files/",
        "thumbnails": {
            "path": "./app/static/thumbs",
            "url": "https://thumbnails.shitposting.space/",
        },
        "uploads": {
            "path": "./app/static/stor",
            "url": "https://useruploads.shitposting.space/",
        },
    },
    "app": {
        "redis_url": "redis://127.0.0.1:6379",
        "secret_key": 'yS\x1c\x88\xd7\xb5\xb0\xdc\t:kO\r\xf0D{"Y\x1f\xbc^\xad',
        "force_https": False,
        "debug": True,
        "development": False,
        "wtf_csrf_time_limit": None,
        "max_content_length": 10485760,  # 10mb
        "fallback_language": "en",
        "testing": False,
    },
    "aws": {},
    "database": {"autoconnect": False},
    "ratelimit": {"default": "60/minute"},
    "notifications": {"fcm_api_key": None},
    "matrix": {"enabled": False},
}


# Nested map of configuration keys which are configurable in the admin
# interface. The accompanying value will only be used in the migration
# which writes that value to the database, and in the tests.
configurable_defaults = {
    "site": {
        "type": "map",
        "value": {
            "name": {
                "type": "string",
                "doc": _l("Name of the site."),
                "value": "Throat",
            },
            "lema": {
                "type": "string",
                "doc": _l("Lema shown in the page's title."),
                "value": "Throat: Open discussion ;D",
            },
            "copyright": {
                "type": "string",
                "doc": _l("Copyright line shown in the footer."),
                "value": "Umbrella Corp",
            },
            "placeholder_account": {
                "type": "string",
                "doc": _l(
                    "Name shown when a sub is owned by a deleted account or abandoned."
                ),
                "value": "Site",
            },
            "enable_security_question": {
                "type": "bool",
                "doc": _l(
                    "Enables setting security questions on the admin page. Users will be "
                    "asked to answer one of these security questions before registering."
                ),
                "value": False,
            },
            "allow_uploads": {
                "type": "bool",
                "doc": _l(
                    "Allow everybody to upload files (by default it's only admins and users "
                    "authorized through a metadata key)."
                ),
                "value": False,
            },
            "allow_video_uploads": {
                "type": "bool",
                "doc": _l(
                    "For those who are allowed to upload files, allow video uploads (.mp4 and .webm) as well."
                ),
                "value": True,
            },
            "upload_min_level": {
                "type": "int",
                "doc": _l(
                    "Minimum level a user must have before being able to upload files. Set to zero "
                    "to disable file upload level limits."
                ),
                "value": 0,
            },
            "enable_chat": {
                "type": "bool",
                "doc": _l(
                    "Allow chat access for all users. If enabled, each user will have the option of "
                    "disabling chat for themselves."
                ),
                "value": True,
            },
            "sitelog_public": {
                "type": "bool",
                "doc": _l(
                    "Allow all users to view the site log. When disabled, only admins can view the sitelog."
                ),
                "value": True,
            },
            "force_sublog_public": {
                "type": "bool",
                "doc": _l(
                    "Forces all the sub logs and banned user lists to be public and removes the "
                    "option to make them private."
                ),
                "value": True,
            },
            "front_page_submit": {
                "type": "bool",
                "doc": _l('Show the "Submit a post" button on the frontpage.'),
                "value": True,
            },
            "block_anon_stalking": {
                "type": "bool",
                "doc": _l(
                    "Blocks anonymous users from being able to look at a particular user's posts or "
                    "comments (IE blocks /u/<user>/posts and /u/<user>/comments)."
                ),
                "value": False,
            },
            "changelog_sub": {
                "type": "string",
                "doc": _l("SID of the sub for changelog entries."),
                "value": "",
            },
            "title_edit_timeout": {
                "type": "int",
                "doc": _l(
                    "Amount of time in seconds the post author can edit a post's title after the "
                    "post was created. Set to zero to disable title editing (default is 5 minutes)."
                ),
                "value": 300,
            },
            "sub_creation_min_level": {
                "type": "int",
                "doc": _l(
                    "Minimum level a user must have before being able to create a sub. Set to zero "
                    "to disable sub creation level limits."
                ),
                "value": 2,
            },
            "sub_creation_admin_only": {
                "type": "bool",
                "doc": _l(
                    "When enabled, only admins can create new subs, otherwise "
                    "`sub_creation_min_level` controls who can create a sub."
                ),
                "value": False,
            },
            "sub_ownership_limit": {
                "type": "int",
                "doc": _l(
                    "Maximum amount of subs a single user can own. The actual amount of subs a user "
                    "may register scales with user level (user level minus one) so a level 0 or "
                    "level 1 user cannot register any subs. This scaling is disabled if "
                    "`sub_creation_min_level` is zero."
                ),
                "value": 20,
            },
            "edit_history": {
                "type": "bool",
                "doc": _l(
                    "Allows Sub Mods and Admins to view the edit history of posts."
                ),
                "value": False,
            },
            "anonymous_modding": {
                "type": "bool",
                "doc": _l(
                    "Removes the name of the Mod or Admin who took action on a post or user in "
                    "notifications sent to user."
                ),
                "value": False,
            },
            "send_pm_to_user_min_level": {
                "type": "int",
                "doc": _l(
                    "Minimum level required for a user to be permitted to private message "
                    "nonprivileged users. Set to zero to allow users of all levels to PM other "
                    "users. Users of any level may PM site admins."
                ),
                "value": 3,
            },
            "daily_sub_posting_limit": {
                "type": "int",
                "doc": _l(
                    "Maximum amount of posts a user can create in a single sub in a day."
                ),
                "value": 10,
            },
            "daily_site_posting_limit": {
                "type": "int",
                "doc": _l("Maximum amount of posts a user can create in a single day."),
                "value": 25,
            },
            "archive_post_after": {
                "type": "int",
                "doc": _l("Number of days after which posts will be archived."),
                "value": 60,
            },
            "archive_sticky_posts": {
                "type": "bool",
                "doc": _l(
                    "When enabled, archive sticky posts after 'archive_post_after' days, "
                    "the same as regular posts. When disabled, sticky posts will not be archived."
                ),
                "value": True,
            },
            "recent_activity": {
                "type": "map",
                "value": {
                    "enabled": {
                        "type": "bool",
                        "doc": _l(
                            "Enables or disables the recent activity sidebar and the page in /activity."
                        ),
                        "value": False,
                    },
                    "defaults_only": {
                        "type": "bool",
                        "doc": _l(
                            "Only show recent activity from default subs in the sidebar (recent "
                            "activity for all subs will be shown in /activity)."
                        ),
                        "value": False,
                    },
                    "comments_only": {
                        "type": "bool",
                        "doc": _l(
                            "If enabled, only show recent comments (and not posts) in the sidebar."
                        ),
                        "value": False,
                    },
                    "max_entries": {
                        "type": "int",
                        "doc": _l(
                            "Number of entries to display in the recent activity sidebar."
                        ),
                        "value": 10,
                    },
                },
            },
            "enable_modmail": {
                "type": "bool",
                "doc": _l(
                    "Show the 'Contact the Mods' button in sub sidebars, which provides "
                    "a link to the modmail server."
                ),
                "value": False,
            },
            "enable_posting": {
                "type": "bool",
                "doc": _l("Allow users to make posts and comments."),
                "value": True,
            },
            "enable_registration": {
                "type": "bool",
                "doc": _l("Allow new users to register."),
                "value": True,
            },
            "invitations_visible_to_users": {
                "type": "bool",
                "doc": _l(
                    "Allow users to see the usernames of the people they invited or were invited by."
                ),
                "value": False,
            },
            "invite_level": {
                "type": "int",
                "doc": _l("Level requirement before a user can generate invite codes."),
                "value": 3,
            },
            "invite_max": {
                "type": "int",
                "doc": _l(
                    "The number of invite codes each user is allowed to generate (see also site.invite_level)."
                ),
                "value": 10,
            },
            "require_captchas": {
                "type": "bool",
                "doc": _l("Require the user to solve a captcha to register or post."),
                "value": True,
            },
            "require_invite_code": {
                "type": "bool",
                "doc": _l("Require an invite code to register."),
                "value": False,
            },
            "notifications_on_icon": {
                "type": "bool",
                "doc": _l(
                    "If enabled, show the notification count on the page title icon.  "
                    "Otherwise, show the notification count in parentheses in the page title."
                ),
                "value": True,
            },
            "username_max_length": {
                "type": "int",
                "doc": _l(
                    "The maximum length of a user name, applied to new registrations. "
                    "This should be set to a number between 2 and 64."
                ),
                "value": 32,
            },
            "nsfw": {
                "type": "map",
                "value": {
                    "anon": {
                        "type": "map",
                        "value": {
                            "show": {
                                "type": "bool",
                                "doc": _l(
                                    "If enabled, show NSFW content to anonymous users."
                                ),
                                "value": True,
                            },
                            "blur": {
                                "type": "bool",
                                "doc": _l(
                                    "If enabled, and 'site.nsfw.anon.show' is also enabled, blur NSFW content "
                                    "when it is shown to anonymous users."
                                ),
                                "value": True,
                            },
                        },
                    },
                    "new_user_default": {
                        "type": "map",
                        "value": {
                            "show": {
                                "type": "bool",
                                "doc": _l(
                                    "If enabled, set the NSFW preference of new users to show NSFW content."
                                ),
                                "value": True,
                            },
                            "blur": {
                                "type": "bool",
                                "doc": _l(
                                    "If enabled, and 'site.nsfw.new_user_default.show' is also enabled, "
                                    "set the NSFW preference of new users to blur NSFW content."
                                ),
                                "value": True,
                            },
                        },
                    },
                },
            },
        },
    },
    "storage": {
        "type": "map",
        "value": {
            "sub_css_max_file_size": {
                "type": "int",
                "doc": _l(
                    "Max storage for image uploads for subs' stylesheets (in MiB)."
                ),
                "value": 2,
            },
        },
    },
}


def add_database_source(cfg_dict):
    """Add the source field to all entries in cfg_dict. Saves some typing
    in the definition of configurable_defaults."""
    for key in cfg_dict:
        if cfg_dict[key]["type"] == "map":
            cfg_dict[key]["source"] = None
            add_database_source(cfg_dict[key]["value"])
        else:
            cfg_dict[key]["source"] = "database"


def add_values_to_config(defaults, values, source):
    """Given a defaults dictionary (structured like configurable_defaults above)
    and a possibly nested config dict, combine the two and return a
    new dict, structured like cfg_defaults.  Every node will have at least
    'type', 'source' and 'value' keys."""
    result = {}
    for key in list(defaults.keys()) + list(values.keys()):
        value = values.get(key)
        default = defaults.get(key)
        if key not in defaults:
            if isinstance(values[key], dict):
                result[key] = {
                    "type": "map",
                    "source": None,
                    "value": add_values_to_config({}, value, source),
                }
            else:
                result[key] = {"type": "any", "source": source, "value": value}
        elif key not in values:
            result[key] = default
        else:
            if default["source"] == "database":
                assert source != "default"
                result[key] = dict(default, configured_value=value)
            elif default["type"] == "map":
                if not isinstance(value, dict):
                    raise TypeError(
                        f"Value found where dict expected at {key}: {value} in {source}"
                    )
                result[key] = {
                    "type": "map",
                    "source": None,
                    "value": add_values_to_config(default["value"], value, source),
                }
            else:
                result[key] = {"type": "any", "source": source, "value": value}
    return result


def get_environment_values(config, prefix=""):
    """Build a dict of values from environment variables with names
    matching the keys in config."""
    new_items = {}
    if len(prefix) > 0:
        for var in os.environ.keys():
            if var.startswith(prefix):
                env_key = var[len(prefix) :].lower()
                env_value = os.environ.get(var)
                existing = config.get(env_key)
                if existing is not None and type(existing["value"]) == int:
                    new_items[env_key] = int(env_value)
                else:
                    new_items[env_key] = env_value
    for key, val in config.items():
        if val["type"] == "map":
            env_vals = get_environment_values(val["value"], prefix + key.upper() + "_")
            if env_vals:
                new_items[key] = env_vals
    return new_items


add_database_source(configurable_defaults)
cfg_defaults = add_values_to_config(configurable_defaults, defaults, "default")


class Map:
    """A dictionary-like object whose keys are accessable as attributes,
    constructed from a nested dictionary structure like
    configurable_defaults defined above.  Supports storing some of the
    values in the database and cache.  Nested maps in the dictionary
    passed at initialization will be converted to nested ConfigMap
    objects."""

    def __init__(
        self,
        sdict,
        model=None,
        cache=None,
        prefixes=None,
    ):
        """Create a Map from the dictionary sdict.

        Mutable values will be stored in the database and cached in
        the cache."""

        self._content = {}
        self._prefixes = [] if prefixes is None else prefixes
        self._model = model
        self._cache = cache

        for key, val in sdict.items():
            self._content[key] = dict(val)
            if val["type"] == "map":
                self._content[key]["value"] = Map(
                    val["value"], model, cache, self._prefixes + [key]
                )

    def get_mutable_items(self):
        """Return mutable keys in this map and all nested maps, along with
        their current value and metadata."""
        result = []
        prefixes = ".".join(self._prefixes) + "."
        for key, val in self._content.items():
            if isinstance(val["value"], Map):
                result = result + val["value"].get_mutable_items()
            elif val["source"] == "database":
                result = result + [
                    {
                        "name": prefixes + key,
                        "value": self.__getattr__(key),
                        "type": val["type"],
                        "doc": val["doc"],
                    }
                ]
        return result

    def mutable_item_configuration(self):
        """Return a list of the full names of all the keys in the map which
        are configurable, and the value set in the config file or
        environment for them if it exists, otherwise the default
        value.  For use by tests and by the migration that moves those
        config file and environment values into SiteMetadata."""
        result = []
        prefixes = self._key_name_from_attr("")
        for key, val in self._content.items():
            if isinstance(val["value"], Map):
                result = result + val["value"].mutable_item_configuration()
            elif val["source"] == "database":
                if "configured_value" in val:
                    value = val["configured_value"]
                else:
                    value = val["value"]
                result = result + [((prefixes + key), value, val["type"])]
        return result

    def _get_from_backing_store(self, attr):
        """Get the value for a key from the cache or the database. Return
        None if no value has been set in the backing store."""
        key = self._key_name_from_attr(attr)
        val = self._cache.get(key)
        if val is None:
            try:
                val = self._model.get(self._model.key == key).value
            except self._model.DoesNotExist:
                # Did you add a new config key? If so, write a migration to
                # add it to SiteMetadata.
                logging.warning(f"{key} is not present in SiteMetadata")
            self._cache.set(key, val)
        return val

    def _key_name_from_attr(self, attr):
        return ".".join(self._prefixes) + "." + attr

    def __getattr__(self, attr):
        if self._content[attr]["source"] == "database":
            val = self._get_from_backing_store(attr)
            if val is None:
                return self._content[attr]["value"]
            else:
                typ = self._content[attr]["type"]
                if typ == "str":
                    return val
                elif typ == "int":
                    return int(val)
                elif typ == "bool":
                    return val == "1"
                else:
                    return val
        return self._content[attr]["value"]

    def __getitem__(self, attr):
        return self.__getattr__(attr)

    def keys(self):
        return self._content.keys()

    def as_dict(self):
        result = {}
        for key, val in self._content.items():
            if isinstance(val["value"], Map):
                result[key] = val["value"].as_dict()
            else:
                result[key] = self.__getattr__(key)
        return result

    def items(self):
        return self.as_dict().items()

    def __contains__(self, attr):
        return attr in self._content

    def get_value(self, attr):
        """Return a value possibly from a nested map named by keys joined by .'s"""
        attrs = attr.split(".")
        if len(attrs) > 1:
            return self._content[attrs[0]]["value"].get_value(".".join(attrs[1:]))
        else:
            return self.__getattr__(attr)

    def _set_value(self, attr, new_value):
        """Set a value possibly in a nested map named by keys joined by .'s"""
        attrs = attr.split(".")
        if len(attrs) > 1:
            return self._content[attrs[0]]["value"]._set_value(
                ".".join(attrs[1:]), new_value
            )
        else:
            self._content[attrs[0]]["value"] = new_value

    def update_value(self, attr, new_val):
        """Set a new value for one of the persistent mutable entries."""
        attrs = attr.split(".")
        if len(attrs) > 1:
            self._content[attrs[0]]["value"].update_value(".".join(attrs[1:]), new_val)
        else:
            prefix = ".".join(self._prefixes)
            if self._content[attr]["source"] != "database":
                raise RuntimeError(
                    f"Config value {prefix}.{attr} cannot be changed at runtime"
                )

            key = self._key_name_from_attr(attr)
            if self._content[attr]["type"] == "bool":
                val = "1" if new_val else "0"
            elif self._content[attr]["type"] == "int":
                # Force a ValueError if an integer can't be parsed.
                val = str(int(new_val))
            else:
                val = new_val
            try:
                rec = self._model.get(self._model.key == key)
                rec.value = val
                rec.save()
            except self._model.DoesNotExist:
                # Did you add a new attribute?  If so use a migration to add it to the database.
                raise RuntimeError(
                    f"Value for config.{prefix}.{attr} is missing from database"
                )
            self._cache.set(key, val)


class Config(Map):
    """ Main config object """

    def __init__(
        self,
        config_filename=None,
        model=None,
        cache=None,
        use_environment=True,
        config_dict=None,
    ):
        if config_filename is None:
            cfg = {}
            if config_dict:
                cfg = config_dict
        else:
            with open(config_filename) as stream:
                cfg = yaml.safe_load(stream)

        config = add_values_to_config(cfg_defaults, cfg, "config")
        if use_environment:
            env = get_environment_values(config)
            config = add_values_to_config(config, env, "environment")

        super(Config, self).__init__(config, model, cache)
        self.check_storage_config()
        self.check_auth_config()
        self.check_ratelimit_config()

    def check_storage_config(self):
        """Adjust our storage config for compatibility with flask-cloudy."""
        storage = self.storage
        if storage.provider == "LOCAL":
            # Make sure our storage paths are absolute.
            if not Path(storage.thumbnails.path).is_absolute():
                self._set_value(
                    "storage.thumbnails.path",
                    f"{Path(__file__).parent.parent.absolute()}/{storage.thumbnails.path}",
                )
            if not Path(storage.uploads.path).is_absolute():
                self._set_value(
                    "storage.uploads.path",
                    f"{Path(__file__).parent.parent.absolute()}/{storage.uploads.path}",
                )
            storage._content["container"] = storage.uploads._content["path"]
            if storage.server:
                if storage.uploads.path != storage.thumbnails.path:
                    logging.warning(
                        "Thumbnails will not be served by local server "
                        "because thumbnails and uploads paths differ"
                    )
                if storage.server_url[-1] == "/":
                    # flask-cloudy does not want the trailing slash
                    self._set_value("storage.server_url", self.storage.server_url[:-1])

        self._set_value("storage.acl", "" if storage.acl is None else storage.acl)

        # This is not for flask-cloudy, just to make config more human-friendly
        if "url" in storage.thumbnails:
            self._set_value(
                "storage.thumbnails.url", ensure_trailing_slash(storage.thumbnails.url)
            )
        if "url" in storage.uploads:
            self._set_value(
                "storage.uploads.url", ensure_trailing_slash(storage.uploads.url)
            )

    def check_auth_config(self):
        if "server" in self.auth.keycloak:
            self._set_value(
                "auth.keycloak.server", ensure_trailing_slash(self.auth.keycloak.server)
            )

    def check_ratelimit_config(self):
        if "storage_url" not in self.ratelimit:
            self.ratelimit._content["storage_url"] = self.app._content["redis_url"]

    def get_flask_dict(self):
        flattened = {}
        for cpk in ["cache", "mail", "sendgrid", "app", "ratelimit"]:
            if cpk in self._content:
                for k in self._content[cpk]["value"].keys():
                    if cpk == "app":
                        key = k.upper()
                    else:
                        key = "{}_{}".format(cpk, k).upper()
                    flattened[key] = self[cpk][k]

        # These values are used by flask-cloudy.
        for key in ["provider", "key", "secret", "container", "server", "server_url"]:
            if key in self.storage.keys():
                flattened[f"STORAGE_{key}".upper()] = self.storage._content[key][
                    "value"
                ]
        return flattened


def ensure_trailing_slash(val):
    """ Add a slash to the string if it doesn't already have one. """
    if val and val[-1] != "/":
        return val + "/"
    else:
        return val


config = LocalProxy(lambda: current_app.config["THROAT_CONFIG"])
