"""Peewee migrations -- 027_federation_remote_sub.py.

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

import peewee as pw


SQL = pw.SQL


def migrate(migrator, database, fake=False, **kwargs):
    """Write your migrations here."""

    @migrator.create_model
    class RemoteSub(pw.Model):
        sid = pw.CharField(max_length=40, primary_key=True)
        name = pw.CharField(max_length=32, null=True, unique=True)
        nsfw = pw.BooleanField(constraints=[SQL("DEFAULT False")])
        sidebar = pw.TextField(constraints=[SQL("DEFAULT ''")])
        status = pw.IntegerField(null=True)
        title = pw.CharField(max_length=50, null=True)
        sort = pw.CharField(max_length=32, null=True)
        creation = pw.DateTimeField()
        subscribers = pw.IntegerField(constraints=[SQL("DEFAULT 1")])
        posts = pw.IntegerField(constraints=[SQL("DEFAULT 0")])
        peer = pw.CharField(max_length=255)
        last_updated = pw.DateTimeField()

        class Meta:
            table_name = "remotesub"


def rollback(migrator, database, fake=False, **kwargs):
    """Write your rollback migrations here."""
    migrator.remove_model("remotesub")
