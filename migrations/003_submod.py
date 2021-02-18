"""Peewee migrations -- 003_submod.py.

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

    @migrator.create_model
    class SubMod(pw.Model):
        id = pw.AutoField()
        uid = pw.ForeignKeyField(
            backref="submod_set",
            column_name="uid",
            field="uid",
            model=migrator.orm["user"],
        )
        sid = pw.ForeignKeyField(
            backref="submod_set",
            column_name="sid",
            field="sid",
            model=migrator.orm["sub"],
        )
        power_level = pw.IntegerField()

        invite = pw.BooleanField(default=False)

        class Meta:
            table_name = "sub_mod"

    if not fake:
        SubMod._meta.database = migrator.database
        SubMod.create_table(True)

        SubMetadata = migrator.orm["sub_metadata"]

        for xm in SubMetadata.select().where(SubMetadata.key == "mod1"):
            SubMod.create(uid=xm.value, sid=xm.sid, power_level=0)

        for xm in SubMetadata.select().where(SubMetadata.key == "mod2"):
            SubMod.create(uid=xm.value, sid=xm.sid, power_level=1)


def rollback(migrator, database, fake=False, **kwargs):
    """Write your rollback migrations here."""

    migrator.remove_model("sub_mod")
