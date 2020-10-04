"""Peewee migrations -- 021_subpostpermissions.py.

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

try:
    import playhouse.postgres_ext as pw_pext
except ImportError:
    pass

SQL = pw.SQL


def migrate(migrator, database, fake=False, **kwargs):
    """Write your migrations here."""
    Sub = migrator.orm['sub']
    SubMetadata = migrator.orm['sub_metadata']

    for sub in Sub.select():
        SubMetadata.create(key='allow_text_posts', value='1', sid=sub.sid)
        SubMetadata.create(key='allow_link_posts', value='1', sid=sub.sid)
        SubMetadata.create(key='allow_upload_posts', value='1', sid=sub.sid)


def rollback(migrator, database, fake=False, **kwargs):
    """Write your rollback migrations here."""
    SubMetadata = migrator.orm['sub_metadata']
    SubMetadata.delete().where(
        SubMetadata.key == 'allow_text_posts').execute()
    SubMetadata.delete().where(
        SubMetadata.key == 'allow_link_posts').execute()
    SubMetadata.delete().where(
        SubMetadata.key == 'allow_upload_posts').execute()
