from peewee import IntegerField, DateTimeField
from peewee import CharField, ForeignKeyField, TextField, PrimaryKeyField
from playhouse.flask_utils import FlaskDB


db = FlaskDB()


class User(db.Model):
    crypto = IntegerField(null=True)
    email = CharField(null=True)
    joindate = DateTimeField(null=True)
    name = CharField(null=True, unique=True)
    password = CharField(null=True)
    score = IntegerField(null=True)  # AKA phuks taken
    given = IntegerField(null=True)  # AKA phuks given
    status = IntegerField(null=True)
    uid = CharField(primary_key=True)
    resets = IntegerField(null=True)

    class Meta:
        db_table = 'user'


class Client(db.Model):
    _default_scopes = TextField(null=True)
    _redirect_uris = TextField(null=True)
    client = CharField(db_column='client_id', primary_key=True)
    client_secret = CharField(unique=True)
    is_confidential = IntegerField(null=True)
    name = CharField(null=True)
    user = ForeignKeyField(db_column='user_id', null=True, rel_model=User,
                           to_field='uid')

    class Meta:
        db_table = 'client'


class Grant(db.Model):
    _scopes = TextField(null=True)
    client = ForeignKeyField(db_column='client_id', rel_model=Client,
                             to_field='client')
    code = CharField(index=True)
    expires = DateTimeField(null=True)
    redirect_uri = CharField(null=True)
    user = ForeignKeyField(db_column='user_id', null=True, rel_model=User,
                           to_field='uid')

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
                                 rel_model=User, to_field='uid')
    sentby = ForeignKeyField(db_column='sentby', null=True, rel_model=User,
                             related_name='user_sentby_set', to_field='uid')
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
    name = CharField(null=True, unique=True)
    nsfw = IntegerField(null=True)
    sid = CharField(primary_key=True)
    sidebar = TextField(null=True)
    status = IntegerField(null=True)
    title = CharField(null=True)
    sort = CharField()
    creation = DateTimeField()

    class Meta:
        db_table = 'sub'


class SubFlair(db.Model):
    sid = ForeignKeyField(db_column='sid', null=True, rel_model=Sub,
                          to_field='sid')
    text = CharField(null=True)
    xid = PrimaryKeyField()

    class Meta:
        db_table = 'sub_flair'


class SubLog(db.Model):
    action = IntegerField(null=True)
    desc = CharField(null=True)
    lid = PrimaryKeyField()
    link = CharField(null=True)
    sid = ForeignKeyField(db_column='sid', null=True, rel_model=Sub,
                          to_field='sid')
    time = DateTimeField(null=True)

    class Meta:
        db_table = 'sub_log'


class SubMetadata(db.Model):
    key = CharField(null=True)
    sid = ForeignKeyField(db_column='sid', null=True, rel_model=Sub,
                          to_field='sid')
    value = CharField(null=True)
    xid = PrimaryKeyField()

    class Meta:
        db_table = 'sub_metadata'


class SubPost(db.Model):
    content = TextField(null=True)
    deleted = IntegerField(null=True)
    link = CharField(null=True)
    nsfw = IntegerField(null=True)
    pid = PrimaryKeyField()
    posted = DateTimeField(null=True)
    ptype = IntegerField(null=True)
    score = IntegerField(null=True)
    sid = ForeignKeyField(db_column='sid', null=True, rel_model=Sub,
                          to_field='sid')
    thumbnail = CharField(null=True)
    title = CharField(null=True)
    comments = IntegerField()
    uid = ForeignKeyField(db_column='uid', null=True, rel_model=User,
                          to_field='uid')

    class Meta:
        db_table = 'sub_post'


class SubPostComment(db.Model):
    cid = CharField(primary_key=True)
    content = TextField(null=True)
    lastedit = DateTimeField(null=True)
    parentcid = ForeignKeyField(db_column='parentcid', null=True,
                                rel_model='self', to_field='cid')
    pid = ForeignKeyField(db_column='pid', null=True, rel_model=SubPost,
                          to_field='pid')
    score = IntegerField(null=True)
    status = IntegerField(null=True)
    time = DateTimeField(null=True)
    uid = ForeignKeyField(db_column='uid', null=True, rel_model=User,
                          to_field='uid')

    class Meta:
        db_table = 'sub_post_comment'


class SubPostCommentVote(db.Model):
    datetime = DateTimeField(null=True)
    cid = CharField(null=True)
    positive = IntegerField(null=True)
    uid = ForeignKeyField(db_column='uid', null=True, rel_model=User,
                          to_field='uid')
    xid = PrimaryKeyField()

    class Meta:
        db_table = 'sub_post_comment_vote'


class SubPostMetadata(db.Model):
    key = CharField(null=True)
    pid = ForeignKeyField(db_column='pid', null=True, rel_model=SubPost,
                          to_field='pid')
    value = CharField(null=True)
    xid = PrimaryKeyField()

    class Meta:
        db_table = 'sub_post_metadata'


class SubPostVote(db.Model):
    datetime = DateTimeField(null=True)
    pid = ForeignKeyField(db_column='pid', null=True, rel_model=SubPost,
                          to_field='pid')
    positive = IntegerField(null=True)
    uid = ForeignKeyField(db_column='uid', null=True, rel_model=User,
                          to_field='uid')
    xid = PrimaryKeyField()

    class Meta:
        db_table = 'sub_post_vote'


class SubStylesheet(db.Model):
    content = TextField(null=True)
    sid = ForeignKeyField(db_column='sid', null=True, rel_model=Sub,
                          to_field='sid')
    xid = PrimaryKeyField()

    class Meta:
        db_table = 'sub_stylesheet'


class SubSubscriber(db.Model):
    order = IntegerField(null=True)
    sid = ForeignKeyField(db_column='sid', null=True, rel_model=Sub,
                          to_field='sid')
    status = IntegerField(null=True)
    time = DateTimeField(null=True)
    uid = ForeignKeyField(db_column='uid', null=True, rel_model=User,
                          to_field='uid')
    xid = PrimaryKeyField()

    class Meta:
        db_table = 'sub_subscriber'


class Token(db.Model):
    _scopes = TextField(null=True)
    access_token = CharField(null=True, unique=True)
    client = ForeignKeyField(db_column='client_id', rel_model=Client,
                             to_field='client')
    expires = DateTimeField(null=True)
    refresh_token = CharField(null=True, unique=True)
    token_type = CharField(null=True)
    user = ForeignKeyField(db_column='user_id', null=True, rel_model=User,
                           to_field='uid')

    class Meta:
        db_table = 'token'


class UserBadge(db.Model):
    badge = CharField(null=True)
    bid = CharField(primary_key=True)
    name = CharField(null=True)
    text = CharField(null=True)
    value = IntegerField(null=True)

    class Meta:
        db_table = 'user_badge'


class UserMetadata(db.Model):
    key = CharField(null=True)
    uid = ForeignKeyField(db_column='uid', null=True, rel_model=User,
                          to_field='uid')
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
    uid = ForeignKeyField(db_column='uid', null=True, rel_model=User,
                          to_field='uid')

    class Meta:
        db_table = 'pixel'


class Shekels(db.Model):
    xid = PrimaryKeyField()
    shekels = IntegerField()
    uid = ForeignKeyField(db_column='uid', null=True, rel_model=User,
                          to_field='uid')

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
