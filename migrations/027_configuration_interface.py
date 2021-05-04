"""Peewee migrations -- 027_configuration_interface.py.

Enter all the config values modifiable in the admin interface into SiteMetadata.

Some examples (model - class or model name)::

    > Model = migrator.orm['model_name']            # Return model in current state by name

    > migrator.sql(sql)                             # Run custom SQL
    > migrator.python(func, *args, **kwargs)        # Run python code
    > migrator.create_model(Model)                  # Create a model (could be used as decorator)
    > migrator.remove_model(model, cascade=True)    # Remove a model
    > migrator.add_fields(model, **fields)          # Add fields to a model
    > migrator.change_fields(model, **fields)       # Change fields
    > migrator.remove_fields(model, *field_names, cascade=True)
    > migrator.rename_field(model, old_field_name, new_field_name)
    > migrator.rename_table(model, new_table_name)
    > migrator.add_index(model, *col_names, unique=False)
    > migrator.drop_index(model, *col_names)
    > migrator.add_not_null(model, *field_names)
    > migrator.drop_not_null(model, *field_names)
    > migrator.add_default(model, field_name, default)

"""

import datetime as dt
import peewee as pw
from decimal import ROUND_HALF_EVEN
from app.config import config

try:
    import playhouse.postgres_ext as pw_pext
except ImportError:
    pass

SQL = pw.SQL

mutable_config_keys = [
    "site.allow_uploads",
    "site.allow_video_uploads",
    "site.anonymous_modding",
    "site.archive_post_after",
    "site.block_anon_stalking",
    "site.changelog_sub",
    "site.copyright",
    "site.daily_site_posting_limit",
    "site.daily_sub_posting_limit",
    "site.edit_history",
    "site.enable_chat",
    "site.enable_security_question",
    "site.force_sublog_public",
    "site.front_page_submit",
    "site.lema",
    "site.name",
    "site.placeholder_account",
    "site.recent_activity.comments_only",
    "site.recent_activity.defaults_only",
    "site.recent_activity.enabled",
    "site.recent_activity.max_entries",
    "site.send_pm_to_user_min_level",
    "site.sitelog_public",
    "site.sub_creation_admin_only",
    "site.sub_creation_min_level",
    "site.sub_ownership_limit",
    "site.title_edit_timeout",
    "site.upload_min_level",
    "storage.sub_css_max_file_size",
]

translate_config_keys = {
    "enable_posting": "site.enable_posting",
    "enable_registration": "site.enable_registration",
    "invitations_visible_to_users": "site.invitations_visible_to_users",
    "invite_level": "site.invite_level",
    "invite_max": "site.invite_max",
    "require_captchas": "site.require_captchas",
    "useinvitecode": "site.require_invite_code",
}

new_defaults = {
    "enable_posting": "1",
    "enable_registration": "1",
    "invitations_visible_to_users": "0",
    "invite_level": "3",
    "invite_max": "10",
    "require_captchas": "1",
    "useinvitecode": "0",
}

reverse_translate = {v: k for k, v in translate_config_keys.items()}


def migrate(migrator, database, fake=False, **kwargs):
    """Write your migrations here."""
    SiteMetadata = migrator.orm["site_metadata"]

    def get_value(rec):
        if rec["type"] == "bool":
            return "1" if rec["value"] else "0"
        else:
            return str(rec["value"])

    if not fake:
        new_records = [
            {"key": m["name"], "value": get_value(m)}
            for m in config.get_mutable_items()
            if m["name"] in mutable_config_keys
        ]
        SiteMetadata.insert_many(new_records).execute()

        existing_records = SiteMetadata.select().where(
            SiteMetadata.key << list(translate_config_keys.keys())
        )
        existing_keys = [rec.key for rec in existing_records]
        for rec in existing_records:
            rec.key = translate_config_keys[rec.key]
            rec.save()
        new_records = [
            {"key": translate_config_keys[k], "value": v}
            for k, v in new_defaults.items()
            if k not in existing_keys
        ]
        SiteMetadata.insert_many(new_records).execute()


def rollback(migrator, database, fake=False, **kwargs):
    """Write your rollback migrations here."""
    SiteMetadata = migrator.orm["site_metadata"]
    if not fake:
        SiteMetadata.delete().where(SiteMetadata.key << mutable_config_keys).execute()

        existing_records = SiteMetadata.select().where(
            SiteMetadata.key << list(reverse_translate.keys())
        )
        for rec in existing_records:
            rec.key = reverse_translate[rec.key]
            rec.save()
