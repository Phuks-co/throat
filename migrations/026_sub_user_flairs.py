"""Peewee migrations -- 026_sub_user_flairs.py.

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
    class SubUserFlairChoice(pw.Model):
        id = pw.AutoField()
        sub = pw.ForeignKeyField(backref='subuserflairchoice_set', column_name='sid', field='sid', model=migrator.orm['sub'])
        flair = pw.CharField(max_length=25)

        class Meta:
            table_name = "sub_user_flair_choice"

    @migrator.create_model
    class SubUserFlair(pw.Model):
        id = pw.AutoField()
        user = pw.ForeignKeyField(backref='subuserflair_set', column_name='uid', field='uid', model=migrator.orm['user'])
        sub = pw.ForeignKeyField(backref='subuserflair_set', column_name='sid', field='sid', model=migrator.orm['sub'])
        flair = pw.CharField(max_length=25)
        flair_choice = pw.ForeignKeyField(backref='subuserflair_set', column_name='flair_choice_id', field='id', model=migrator.orm['sub_user_flair_choice'], null=True)

        class Meta:
            table_name = "sub_user_flair"


def rollback(migrator, database, fake=False, **kwargs):
    """Write your rollback migrations here."""

    migrator.remove_model('sub_user_flair')

    migrator.remove_model('sub_user_flair_choice')
