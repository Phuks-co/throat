"""Peewee migrations -- 001_initial.py.
"""

import datetime as dt
import peewee as pw
from decimal import ROUND_HALF_EVEN

SQL = pw.SQL


def migrate(migrator, database, fake=False, **kwargs):
    """Write your migrations here."""

    @migrator.create_model
    class User(pw.Model):
        uid = pw.CharField(max_length=40, primary_key=True)
        crypto = pw.IntegerField()
        email = pw.CharField(max_length=255, null=True)
        joindate = pw.DateTimeField(null=True)
        name = pw.CharField(max_length=64, null=True, unique=True)
        password = pw.CharField(max_length=255, null=True)
        score = pw.IntegerField(constraints=[SQL("DEFAULT 0")])
        given = pw.IntegerField(constraints=[SQL("DEFAULT 0")])
        status = pw.IntegerField(constraints=[SQL("DEFAULT 0")])
        resets = pw.IntegerField(constraints=[SQL("DEFAULT 0")])

        class Meta:
            table_name = "user"

    @migrator.create_model
    class APIToken(pw.Model):
        id = pw.AutoField()
        user = pw.ForeignKeyField(backref='apitoken_set', column_name='uid', field='uid', model=migrator.orm['user'])
        token = pw.CharField(max_length=255, unique=True)
        can_post = pw.BooleanField()
        can_mod = pw.BooleanField()
        can_message = pw.BooleanField()
        can_upload = pw.BooleanField()
        is_active = pw.BooleanField(constraints=[SQL("DEFAULT True")])
        is_ip_restricted = pw.BooleanField(constraints=[SQL("DEFAULT False")])

        class Meta:
            table_name = "api_token"

    @migrator.create_model
    class APITokenSettings(pw.Model):
        id = pw.AutoField()
        token = pw.ForeignKeyField(backref='apitokensettings_set', column_name='token_id', field='id', model=migrator.orm['api_token'])
        key = pw.CharField(max_length=255)
        value = pw.CharField(max_length=255)

        class Meta:
            table_name = "api_token_settings"

    @migrator.create_model
    class Client(pw.Model):
        client = pw.CharField(column_name='client_id', max_length=40, primary_key=True)
        _default_scopes = pw.TextField(null=True)
        _redirect_uris = pw.TextField(null=True)
        client_secret = pw.CharField(max_length=55, unique=True)
        is_confidential = pw.BooleanField(null=True)
        name = pw.CharField(max_length=40, null=True)
        user = pw.ForeignKeyField(backref='client_set', column_name='user_id', field='uid', model=migrator.orm['user'], null=True)

        class Meta:
            table_name = "client"

    @migrator.create_model
    class Grant(pw.Model):
        id = pw.AutoField()
        _scopes = pw.TextField(null=True)
        client = pw.ForeignKeyField(backref='grant_set', column_name='client_id', field='client', model=migrator.orm['client'])
        code = pw.CharField(index=True, max_length=255)
        expires = pw.DateTimeField(null=True)
        redirect_uri = pw.CharField(max_length=255, null=True)
        user = pw.ForeignKeyField(backref='grant_set', column_name='user_id', field='uid', model=migrator.orm['user'], null=True)

        class Meta:
            table_name = "grant"

    @migrator.create_model
    class Message(pw.Model):
        mid = pw.PrimaryKeyField()
        content = pw.TextField(null=True)
        mlink = pw.CharField(max_length=255, null=True)
        mtype = pw.IntegerField(null=True)
        posted = pw.DateTimeField(null=True)
        read = pw.DateTimeField(null=True)
        receivedby = pw.ForeignKeyField(backref='message_set', column_name='receivedby', field='uid', model=migrator.orm['user'], null=True)
        sentby = pw.ForeignKeyField(backref='user_sentby_set', column_name='sentby', field='uid', model=migrator.orm['user'], null=True)
        subject = pw.CharField(max_length=255, null=True)

        class Meta:
            table_name = "message"

    @migrator.create_model
    class SiteLog(pw.Model):
        lid = pw.PrimaryKeyField()
        action = pw.IntegerField(null=True)
        desc = pw.CharField(max_length=255, null=True)
        link = pw.CharField(max_length=255, null=True)
        time = pw.DateTimeField()
        uid = pw.ForeignKeyField(backref='sitelog_set', column_name='uid', field='uid', model=migrator.orm['user'], null=True)
        target = pw.ForeignKeyField(backref='sitelog_set', column_name='target_uid', field='uid', model=migrator.orm['user'], null=True)

        class Meta:
            table_name = "site_log"

    @migrator.create_model
    class SiteMetadata(pw.Model):
        xid = pw.PrimaryKeyField()
        key = pw.CharField(max_length=255, null=True)
        value = pw.CharField(max_length=255, null=True)

        class Meta:
            table_name = "site_metadata"

    @migrator.create_model
    class Sub(pw.Model):
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

        class Meta:
            table_name = "sub"

    @migrator.create_model
    class SubFlair(pw.Model):
        xid = pw.PrimaryKeyField()
        sid = pw.ForeignKeyField(backref='subflair_set', column_name='sid', field='sid', model=migrator.orm['sub'], null=True)
        text = pw.CharField(max_length=255, null=True)

        class Meta:
            table_name = "sub_flair"

    @migrator.create_model
    class SubLog(pw.Model):
        lid = pw.PrimaryKeyField()
        action = pw.IntegerField(null=True)
        desc = pw.CharField(max_length=255, null=True)
        link = pw.CharField(max_length=255, null=True)
        sid = pw.ForeignKeyField(backref='sublog_set', column_name='sid', field='sid', model=migrator.orm['sub'], null=True)
        uid = pw.ForeignKeyField(backref='sublog_set', column_name='uid', field='uid', model=migrator.orm['user'], null=True)
        target = pw.ForeignKeyField(backref='sublog_set', column_name='target_uid', field='uid', model=migrator.orm['user'], null=True)
        admin = pw.BooleanField(constraints=[SQL("DEFAULT False")])
        time = pw.DateTimeField()

        class Meta:
            table_name = "sub_log"

    @migrator.create_model
    class SubMetadata(pw.Model):
        xid = pw.PrimaryKeyField()
        key = pw.CharField(max_length=255, null=True)
        sid = pw.ForeignKeyField(backref='submetadata_set', column_name='sid', field='sid', model=migrator.orm['sub'], null=True)
        value = pw.CharField(max_length=255, null=True)

        class Meta:
            table_name = "sub_metadata"

    @migrator.create_model
    class SubPost(pw.Model):
        pid = pw.PrimaryKeyField()
        content = pw.TextField(null=True)
        deleted = pw.IntegerField(null=True)
        link = pw.CharField(max_length=255, null=True)
        nsfw = pw.BooleanField(null=True)
        posted = pw.DateTimeField(null=True)
        edited = pw.DateTimeField(null=True)
        ptype = pw.IntegerField(null=True)
        score = pw.IntegerField(null=True)
        upvotes = pw.IntegerField(constraints=[SQL("DEFAULT 0")])
        downvotes = pw.IntegerField(constraints=[SQL("DEFAULT 0")])
        sid = pw.ForeignKeyField(backref='subpost_set', column_name='sid', field='sid', model=migrator.orm['sub'], null=True)
        thumbnail = pw.CharField(max_length=255, null=True)
        title = pw.CharField(max_length=255, null=True)
        comments = pw.IntegerField()
        uid = pw.ForeignKeyField(backref='posts', column_name='uid', field='uid', model=migrator.orm['user'], null=True)
        flair = pw.CharField(max_length=25, null=True)

        class Meta:
            table_name = "sub_post"

    @migrator.create_model
    class SubPostComment(pw.Model):
        cid = pw.CharField(max_length=40, primary_key=True)
        content = pw.TextField(null=True)
        lastedit = pw.DateTimeField(null=True)
        parentcid = pw.ForeignKeyField(backref='subpostcomment_set', column_name='parentcid', field='cid', model=migrator.orm['sub_post_comment'], null=True)
        pid = pw.ForeignKeyField(backref='subpostcomment_set', column_name='pid', field='pid', model=migrator.orm['sub_post'], null=True)
        score = pw.IntegerField(null=True)
        upvotes = pw.IntegerField(constraints=[SQL("DEFAULT 0")])
        downvotes = pw.IntegerField(constraints=[SQL("DEFAULT 0")])
        status = pw.IntegerField(null=True)
        time = pw.DateTimeField(null=True)
        uid = pw.ForeignKeyField(backref='comments', column_name='uid', field='uid', model=migrator.orm['user'], null=True)

        class Meta:
            table_name = "sub_post_comment"

    @migrator.create_model
    class SubPostCommentReport(pw.Model):
        id = pw.AutoField()
        cid = pw.ForeignKeyField(backref='subpostcommentreport_set', column_name='cid', field='cid', model=migrator.orm['sub_post_comment'])
        uid = pw.ForeignKeyField(backref='subpostcommentreport_set', column_name='uid', field='uid', model=migrator.orm['user'])
        datetime = pw.DateTimeField()
        reason = pw.CharField(max_length=128)

        class Meta:
            table_name = "sub_post_comment_report"

    @migrator.create_model
    class SubPostCommentVote(pw.Model):
        xid = pw.PrimaryKeyField()
        datetime = pw.DateTimeField(null=True)
        cid = pw.CharField(max_length=255, null=True)
        positive = pw.IntegerField(null=True)
        uid = pw.ForeignKeyField(backref='subpostcommentvote_set', column_name='uid', field='uid', model=migrator.orm['user'], null=True)

        class Meta:
            table_name = "sub_post_comment_vote"

    @migrator.create_model
    class SubPostMetadata(pw.Model):
        xid = pw.PrimaryKeyField()
        key = pw.CharField(max_length=255, null=True)
        pid = pw.ForeignKeyField(backref='subpostmetadata_set', column_name='pid', field='pid', model=migrator.orm['sub_post'], null=True)
        value = pw.CharField(max_length=255, null=True)

        class Meta:
            table_name = "sub_post_metadata"

    @migrator.create_model
    class SubPostPollOption(pw.Model):
        id = pw.AutoField()
        pid = pw.ForeignKeyField(backref='subpostpolloption_set', column_name='pid', field='pid', model=migrator.orm['sub_post'])
        text = pw.CharField(max_length=255)

        class Meta:
            table_name = "sub_post_poll_option"

    @migrator.create_model
    class SubPostPollVote(pw.Model):
        id = pw.AutoField()
        pid = pw.ForeignKeyField(backref='subpostpollvote_set', column_name='pid', field='pid', model=migrator.orm['sub_post'])
        uid = pw.ForeignKeyField(backref='subpostpollvote_set', column_name='uid', field='uid', model=migrator.orm['user'])
        vid = pw.ForeignKeyField(backref='votes', column_name='vid', field='id', model=migrator.orm['sub_post_poll_option'])

        class Meta:
            table_name = "sub_post_poll_vote"

    @migrator.create_model
    class SubPostReport(pw.Model):
        id = pw.AutoField()
        pid = pw.ForeignKeyField(backref='subpostreport_set', column_name='pid', field='pid', model=migrator.orm['sub_post'])
        uid = pw.ForeignKeyField(backref='subpostreport_set', column_name='uid', field='uid', model=migrator.orm['user'])
        datetime = pw.DateTimeField()
        reason = pw.CharField(max_length=128)

        class Meta:
            table_name = "sub_post_report"

    @migrator.create_model
    class SubPostVote(pw.Model):
        xid = pw.PrimaryKeyField()
        datetime = pw.DateTimeField(null=True)
        pid = pw.ForeignKeyField(backref='votes', column_name='pid', field='pid', model=migrator.orm['sub_post'], null=True)
        positive = pw.IntegerField(null=True)
        uid = pw.ForeignKeyField(backref='subpostvote_set', column_name='uid', field='uid', model=migrator.orm['user'], null=True)

        class Meta:
            table_name = "sub_post_vote"

    @migrator.create_model
    class SubStylesheet(pw.Model):
        xid = pw.PrimaryKeyField()
        content = pw.TextField(null=True)
        source = pw.TextField()
        sid = pw.ForeignKeyField(backref='substylesheet_set', column_name='sid', field='sid', model=migrator.orm['sub'], null=True)

        class Meta:
            table_name = "sub_stylesheet"

    @migrator.create_model
    class SubSubscriber(pw.Model):
        xid = pw.PrimaryKeyField()
        order = pw.IntegerField(null=True)
        sid = pw.ForeignKeyField(backref='subsubscriber_set', column_name='sid', field='sid', model=migrator.orm['sub'], null=True)
        status = pw.IntegerField(null=True)
        time = pw.DateTimeField()
        uid = pw.ForeignKeyField(backref='subsubscriber_set', column_name='uid', field='uid', model=migrator.orm['user'], null=True)

        class Meta:
            table_name = "sub_subscriber"

    @migrator.create_model
    class SubUploads(pw.Model):
        id = pw.AutoField()
        sid = pw.ForeignKeyField(backref='subuploads_set', column_name='sid', field='sid', model=migrator.orm['sub'])
        fileid = pw.CharField(max_length=255)
        thumbnail = pw.CharField(max_length=255)
        name = pw.CharField(max_length=255)
        size = pw.IntegerField()

        class Meta:
            table_name = "sub_uploads"

    @migrator.create_model
    class Token(pw.Model):
        id = pw.AutoField()
        _scopes = pw.TextField(null=True)
        access_token = pw.CharField(max_length=100, null=True, unique=True)
        client = pw.ForeignKeyField(backref='token_set', column_name='client_id', field='client', model=migrator.orm['client'])
        expires = pw.DateTimeField(null=True)
        refresh_token = pw.CharField(max_length=100, null=True, unique=True)
        token_type = pw.CharField(max_length=40, null=True)
        user = pw.ForeignKeyField(backref='token_set', column_name='user_id', field='uid', model=migrator.orm['user'], null=True)

        class Meta:
            table_name = "token"

    @migrator.create_model
    class UserIgnores(pw.Model):
        id = pw.AutoField()
        uid = pw.ForeignKeyField(backref='userignores_set', column_name='uid', field='uid', model=migrator.orm['user'])
        target = pw.CharField(max_length=40)
        date = pw.DateTimeField()

        class Meta:
            table_name = "user_ignores"

    @migrator.create_model
    class UserMetadata(pw.Model):
        xid = pw.PrimaryKeyField()
        key = pw.CharField(max_length=255, null=True)
        uid = pw.ForeignKeyField(backref='usermetadata_set', column_name='uid', field='uid', model=migrator.orm['user'], null=True)
        value = pw.CharField(max_length=255, null=True)

        class Meta:
            table_name = "user_metadata"

    @migrator.create_model
    class UserSaved(pw.Model):
        xid = pw.PrimaryKeyField()
        pid = pw.IntegerField(null=True)
        uid = pw.ForeignKeyField(backref='usersaved_set', column_name='uid', field='uid', model=migrator.orm['user'], null=True)

        class Meta:
            table_name = "user_saved"

    @migrator.create_model
    class UserUploads(pw.Model):
        xid = pw.PrimaryKeyField()
        pid = pw.ForeignKeyField(backref='useruploads_set', column_name='pid', field='pid', model=migrator.orm['sub_post'], null=True)
        uid = pw.ForeignKeyField(backref='useruploads_set', column_name='uid', field='uid', model=migrator.orm['user'], null=True)
        fileid = pw.CharField(max_length=255, null=True)
        thumbnail = pw.CharField(max_length=255, null=True)
        status = pw.IntegerField()

        class Meta:
            table_name = "user_uploads"



def rollback(migrator, database, fake=False, **kwargs):
    """Write your rollback migrations here."""

    migrator.remove_model('user_uploads')

    migrator.remove_model('shekels')

    migrator.remove_model('user_metadata')

    migrator.remove_model('user_ignores')

    migrator.remove_model('token')

    migrator.remove_model('sub_uploads')

    migrator.remove_model('sub_subscriber')

    migrator.remove_model('sub_stylesheet')

    migrator.remove_model('sub_post_vote')

    migrator.remove_model('sub_post_report')

    migrator.remove_model('sub_post_poll_vote')

    migrator.remove_model('sub_post_poll_option')

    migrator.remove_model('sub_post_metadata')

    migrator.remove_model('sub_post_comment_vote')

    migrator.remove_model('sub_post_comment_report')

    migrator.remove_model('sub_post_comment')

    migrator.remove_model('sub_post')

    migrator.remove_model('sub_metadata')

    migrator.remove_model('sub_log')

    migrator.remove_model('sub_flair')

    migrator.remove_model('sub')

    migrator.remove_model('site_metadata')

    migrator.remove_model('site_log')

    migrator.remove_model('message')

    migrator.remove_model('user')

    migrator.remove_model('grant')

    migrator.remove_model('client')

    migrator.remove_model('api_token_settings')

    migrator.remove_model('api_token')
