"""Peewee migrations -- 024_unstick_deleted_posts.py.

Remove 'sticky' metadata from deleted posts.
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

    SubMetadata = migrator.orm["sub_metadata"]
    SubPost = migrator.orm["sub_post"]

    if not fake:
        sticky = (
            SubMetadata.select()
            .join(
                SubPost,
                pw.JOIN.LEFT_OUTER,
                on=(SubPost.pid == SubMetadata.value.cast("int")),
            )
            .where((SubMetadata.key == "sticky") & (SubPost.deleted != 0))
        )
        SubMetadata.delete().where(
            SubMetadata.xid << [smd.xid for smd in sticky]
        ).execute()


def rollback(migrator, database, fake=False, **kwargs):
    """Write your rollback migrations here."""
    pass
