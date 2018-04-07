import datetime
from peewee import IntegerField, DateTimeField, BooleanField
from peewee import CharField, ForeignKeyField, TextField, PrimaryKeyField
from playhouse.flask_utils import FlaskDB
import config
import redis

# Why not here? >_>
rconn = redis.from_url(config.SOCKETIO_REDIS_URL)


db = FlaskDB()


class User(db.Model):
    uid = CharField(primary_key=True, max_length=40)
    crypto = IntegerField()
    email = CharField(null=True)
    joindate = DateTimeField(null=True)
    name = CharField(null=True, unique=True, max_length=64)
    password = CharField(null=True)

    score = IntegerField(default=0)  # AKA phuks taken
    given = IntegerField(default=0)  # AKA phuks given
    # status: 0 = OK; 10 = deleted
    status = IntegerField(default=0)
    resets = IntegerField(default=0)

    class Meta:
        db_table = 'user'


class Client(db.Model):
    _default_scopes = TextField(null=True)
    _redirect_uris = TextField(null=True)
    client = CharField(db_column='client_id', primary_key=True, max_length=40)
    client_secret = CharField(unique=True, max_length=55)
    is_confidential = BooleanField(null=True)
    name = CharField(null=True, max_length=40)
    user = ForeignKeyField(db_column='user_id', null=True, model=User, field='uid')

    class Meta:
        db_table = 'client'


class Grant(db.Model):
    _scopes = TextField(null=True)
    client = ForeignKeyField(db_column='client_id', model=Client, field='client')
    code = CharField(index=True)
    expires = DateTimeField(null=True)
    redirect_uri = CharField(null=True)
    user = ForeignKeyField(db_column='user_id', null=True, model=User,
                           field='uid')

    class Meta:
        db_table = 'grant'


class Message(db.Model):
    content = TextField(null=True)
    mid = PrimaryKeyField()
    mlink = CharField(null=True)
    mtype = IntegerField(null=True)
    posted = DateTimeField(null=True)
    read = DateTimeField(null=True)
    receivedby = ForeignKeyField(db_column='receivedby', null=True,
                                 model=User, field='uid')
    sentby = ForeignKeyField(db_column='sentby', null=True, model=User,
                             backref='user_sentby_set', field='uid')
    subject = CharField(null=True)

    class Meta:
        db_table = 'message'


class SiteLog(db.Model):
    action = IntegerField(null=True)
    desc = CharField(null=True)
    lid = PrimaryKeyField()
    link = CharField(null=True)
    time = DateTimeField(null=True)

    class Meta:
        db_table = 'site_log'


class SiteMetadata(db.Model):
    key = CharField(null=True)
    value = CharField(null=True)
    xid = PrimaryKeyField()

    class Meta:
        db_table = 'site_metadata'


class Sub(db.Model):
    name = CharField(null=True, unique=True, max_length=32)
    nsfw = BooleanField(null=True)
    sid = CharField(primary_key=True, max_length=40)
    sidebar = TextField(null=True)
    status = IntegerField(null=True)
    title = CharField(null=True, max_length=50)
    sort = CharField(null=True, max_length=32)
    creation = DateTimeField()
    subscribers = IntegerField(null=True)
    posts = IntegerField(null=True)

    class Meta:
        db_table = 'sub'


class SubFlair(db.Model):
    sid = ForeignKeyField(db_column='sid', null=True, model=Sub,
                          field='sid')
    text = CharField(null=True)
    xid = PrimaryKeyField()

    class Meta:
        db_table = 'sub_flair'


class SubLog(db.Model):
    action = IntegerField(null=True)
    desc = CharField(null=True)
    lid = PrimaryKeyField()
    link = CharField(null=True)
    sid = ForeignKeyField(db_column='sid', null=True, model=Sub,
                          field='sid')
    time = DateTimeField(null=True)

    class Meta:
        db_table = 'sub_log'


class SubMetadata(db.Model):
    key = CharField(null=True)
    sid = ForeignKeyField(db_column='sid', null=True, model=Sub,
                          field='sid')
    value = CharField(null=True)
    xid = PrimaryKeyField()

    class Meta:
        db_table = 'sub_metadata'


class SubPost(db.Model):
    content = TextField(null=True)
    deleted = IntegerField(null=True)
    link = CharField(null=True)
    nsfw = BooleanField(null=True)
    pid = PrimaryKeyField()
    posted = DateTimeField(null=True)
    ptype = IntegerField(null=True)
    score = IntegerField(null=True)
    sid = ForeignKeyField(db_column='sid', null=True, model=Sub,
                          field='sid')
    thumbnail = CharField(null=True)
    title = CharField(null=True)
    comments = IntegerField()
    uid = ForeignKeyField(db_column='uid', null=True, model=User,
                          field='uid')
    flair = CharField(null=True, max_length=25)

    class Meta:
        db_table = 'sub_post'


class SubPostComment(db.Model):
    cid = CharField(primary_key=True, max_length=40)
    content = TextField(null=True)
    lastedit = DateTimeField(null=True)
    parentcid = ForeignKeyField(db_column='parentcid', null=True,
                                model='self', field='cid')
    pid = ForeignKeyField(db_column='pid', null=True, model=SubPost,
                          field='pid')
    score = IntegerField(null=True)
    status = IntegerField(null=True)
    time = DateTimeField(null=True)
    uid = ForeignKeyField(db_column='uid', null=True, model=User,
                          field='uid')

    class Meta:
        db_table = 'sub_post_comment'


class SubPostCommentVote(db.Model):
    datetime = DateTimeField(null=True)
    cid = CharField(null=True)
    positive = IntegerField(null=True)
    uid = ForeignKeyField(db_column='uid', null=True, model=User,
                          field='uid')
    xid = PrimaryKeyField()

    class Meta:
        db_table = 'sub_post_comment_vote'


class SubPostMetadata(db.Model):
    key = CharField(null=True)
    pid = ForeignKeyField(db_column='pid', null=True, model=SubPost,
                          field='pid')
    value = CharField(null=True)
    xid = PrimaryKeyField()

    class Meta:
        db_table = 'sub_post_metadata'


class SubPostVote(db.Model):
    datetime = DateTimeField(null=True)
    pid = ForeignKeyField(db_column='pid', null=True, model=SubPost,
                          field='pid')
    positive = IntegerField(null=True)
    uid = ForeignKeyField(db_column='uid', null=True, model=User,
                          field='uid')
    xid = PrimaryKeyField()

    class Meta:
        db_table = 'sub_post_vote'


class SubStylesheet(db.Model):
    content = TextField(null=True)
    sid = ForeignKeyField(db_column='sid', null=True, model=Sub,
                          field='sid')
    xid = PrimaryKeyField()

    class Meta:
        db_table = 'sub_stylesheet'


class SubSubscriber(db.Model):
    order = IntegerField(null=True)
    sid = ForeignKeyField(db_column='sid', null=True, model=Sub,
                          field='sid')
    status = IntegerField(null=True)
    time = DateTimeField(null=True)
    uid = ForeignKeyField(db_column='uid', null=True, model=User,
                          field='uid')
    xid = PrimaryKeyField()

    class Meta:
        db_table = 'sub_subscriber'


class Token(db.Model):
    _scopes = TextField(null=True)
    access_token = CharField(null=True, unique=True, max_length=100)
    client = ForeignKeyField(db_column='client_id', model=Client,
                             field='client')
    expires = DateTimeField(null=True)
    refresh_token = CharField(null=True, unique=True, max_length=100)
    token_type = CharField(null=True, max_length=40)
    user = ForeignKeyField(db_column='user_id', null=True, model=User,
                           field='uid')

    class Meta:
        db_table = 'token'


class UserBadge(db.Model):
    badge = CharField(null=True)
    bid = CharField(primary_key=True, max_length=40)
    name = CharField(null=True, max_length=40)
    text = CharField(null=True)
    value = IntegerField(null=True)

    class Meta:
        db_table = 'user_badge'


class UserMetadata(db.Model):
    key = CharField(null=True)
    uid = ForeignKeyField(db_column='uid', null=True, model=User,
                          field='uid')
    value = CharField(null=True)
    xid = PrimaryKeyField()

    class Meta:
        db_table = 'user_metadata'


class UserSaved(db.Model):
    pid = IntegerField(null=True)
    uid = CharField(null=True)
    xid = PrimaryKeyField()

    class Meta:
        db_table = 'user_saved'


class Pixel(db.Model):
    xid = PrimaryKeyField()
    posx = IntegerField()
    posy = IntegerField()
    value = IntegerField()
    color = IntegerField()
    uid = ForeignKeyField(db_column='uid', null=True, model=User,
                          field='uid')

    class Meta:
        db_table = 'pixel'


class Shekels(db.Model):
    xid = PrimaryKeyField()
    shekels = IntegerField()
    uid = ForeignKeyField(db_column='uid', null=True, model=User,
                          field='uid')

    class Meta:
        db_table = 'shekels'


class MiningLeaderboard(db.Model):
    xid = PrimaryKeyField()
    username = CharField()  # TODO: MAKE UNIQUE!!
    score = IntegerField()

    class Meta:
        db_table = 'mining_leaderboard'


class MiningSpeedLeaderboard(db.Model):
    username = CharField()  # TODO: MAKE UNIQUE!!
    hashes = IntegerField()

    class Meta:
        db_table = 'mining_speed_leaderboard'


class UserUploads(db.Model):
    xid = PrimaryKeyField()
    pid = ForeignKeyField(db_column='pid', null=True, model=SubPost,
                          field='pid')
    uid = ForeignKeyField(db_column='uid', null=True, model=User,
                          field='uid')
    fileid = CharField(null=True)
    thumbnail = CharField(null=True)
    status = IntegerField()

    class Meta:
        db_table = 'user_uploads'
