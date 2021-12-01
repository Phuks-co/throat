"""Peewee migrations -- 038_best_comment_sort.py

Add a new table to keep track of whether a user has viewed a comment.
Add fields to SubPostComment to cache how many users have viewed each
comment, and to cache the calculated "best" score.

"""
import datetime as dt
import peewee as pw

SQL = pw.SQL


def migrate(migrator, database, fake=False, **kwargs):
    SubPost = migrator.orm["sub_post"]
    SubPostComment = migrator.orm["sub_post_comment"]
    User = migrator.orm["user"]

    @migrator.create_model
    class SubPostCommentView(pw.Model):
        cid = pw.ForeignKeyField(db_column="cid", model=SubPostComment, field="cid")
        uid = pw.ForeignKeyField(db_column="uid", model=User, field="uid")
        pid = pw.ForeignKeyField(db_column="pid", model=SubPost, field="pid")

        class Meta:
            table_name = "sub_post_comment_view"

    # peewee_migrate's add_index does not work if you set db_column when creating
    # a ForeignKeyField.
    ctx = database.get_sql_context()
    idx = pw.Index(
        "subpostcommentview_cid_uid",
        "sub_post_comment_view",
        [SubPostCommentView.cid, SubPostCommentView.uid],
        unique=True,
    )
    migrator.sql("".join(ctx.sql(idx)._sql))

    migrator.add_fields(
        SubPostComment,
        best_score=pw.FloatField(null=True),
        views=pw.IntegerField(default=0),
    )

    if not fake:
        SiteMetadata = migrator.orm["site_metadata"]
        SiteMetadata.create(
            key="best_comment_sort_init",
            value=dt.datetime.utcnow().strftime("%Y-%m-%UdT%H:%M:%SZ"),
        )


def rollback(migrator, database, fake=False, **kwargs):
    migrator.remove_model("sub_post_comment_view")
    migrator.remove_fields("sub_post_comment", "views", "best_score")

    if not fake:
        SiteMetadata = migrator.orm["site_metadata"]
        SiteMetadata.delete().where(
            SiteMetadata.key == "best_comment_sort_init"
        ).execute()
