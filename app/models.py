""" Database and storage related functions and classes """
import datetime
import time
import logging
from enum import IntEnum
import functools
import sys
from flask import g
from flask_redis import FlaskRedis
from peewee import IntegerField, DateTimeField, BooleanField, Proxy, Model, Database
from peewee import CharField, ForeignKeyField, TextField, PrimaryKeyField, FloatField
from werkzeug.local import LocalProxy
from .storage import file_url
from .config import config

rconn = FlaskRedis()

dbp = Proxy()


def get_db():
    if "db" not in g:
        if dbp.is_closed():
            dbp.connect()
        g.db = dbp
    return g.db


db = LocalProxy(get_db)


def db_init_app(app):
    dbconnect = app.config["THROAT_CONFIG"].database.as_dict()
    # Taken from peewee's flask_utils
    try:
        name = dbconnect.pop("name")
        engine = dbconnect.pop("engine")
    except KeyError:
        raise RuntimeError("DATABASE configuration must specify a `name` and `engine`.")

    if "." in engine:
        path, class_name = engine.rsplit(".", 1)
    else:
        path, class_name = "peewee", engine

    try:
        __import__(path)
        module = sys.modules[path]
        database_class = getattr(module, class_name)
        assert issubclass(database_class, Database)
    except ImportError:
        raise RuntimeError("Unable to import %s" % engine)
    except AttributeError:
        raise RuntimeError("Database engine not found %s" % engine)
    except AssertionError:
        raise RuntimeError(
            "Database engine not a subclass of peewee.Database: %s" % engine
        )

    dbm = database_class(name, **dbconnect)
    dbm.execute_sql = functools.partial(peewee_count_queries, dbm.execute_sql)
    dbp.initialize(dbm)

    @app.teardown_appcontext
    def close_db(_):
        dbp = g.pop("db", None)
        if dbp is not None:
            dbp.close()


timing_logger = logging.getLogger("app.sql_timing")


def peewee_count_queries(dex, sql, *args, **kwargs):
    """ Used to count and display number of queries """
    try:
        if not hasattr(g, "pqc"):
            g.pqc = 0
        g.pqc += 1
    except RuntimeError:
        pass
    starttime = time.time()
    try:
        result = dex(sql, *args, **kwargs)
    finally:
        timing_logger.debug(
            "(%s, %s) (executed in %s ms)",
            sql,
            args[0] if len(args) > 0 else kwargs.get("params"),
            int((time.time() - starttime) * 1000),
        )
    return result


class BaseModel(Model):
    class Meta:
        database = db


class UserCrypto(IntEnum):
    """Password hash algorithm."""

    BCRYPT = 1
    REMOTE = 2  # password stored on remote auth server


class UserStatus(IntEnum):
    """User's login capability status."""

    OK = 0
    PROBATION = 1  # New, with email not yet confirmed.
    BANNED = 5  # site-ban
    DELETED = 10


class User(BaseModel):
    uid = CharField(primary_key=True, max_length=40)
    crypto = IntegerField()  # Password hash algo, 1 = bcrypt.
    email = CharField(null=True)
    joindate = DateTimeField(null=True)
    name = CharField(null=True, unique=True, max_length=64)
    password = CharField(null=True)

    score = IntegerField(default=0)  # AKA phuks taken
    given = IntegerField(default=0)  # AKA phuks given
    # status: 0 = OK; 10 = deleted; 5 = site-ban
    status = IntegerField(default=0)
    resets = IntegerField(default=0)

    language = CharField(default=None, null=True, max_length=11)

    def __repr__(self):
        return f"<User {self.name}>"

    class Meta:
        table_name = "user"


class Client(BaseModel):
    _default_scopes = TextField(null=True)
    _redirect_uris = TextField(null=True)
    client = CharField(db_column="client_id", primary_key=True, max_length=40)
    client_secret = CharField(unique=True, max_length=55)
    is_confidential = BooleanField(null=True)
    name = CharField(null=True, max_length=40)
    user = ForeignKeyField(db_column="user_id", null=True, model=User, field="uid")

    def __repr__(self):
        return f"<Client {self.name}>"

    class Meta:
        table_name = "client"


class Grant(BaseModel):
    _scopes = TextField(null=True)
    client = ForeignKeyField(db_column="client_id", model=Client, field="client")
    code = CharField(index=True)
    expires = DateTimeField(null=True)
    redirect_uri = CharField(null=True)
    user = ForeignKeyField(db_column="user_id", null=True, model=User, field="uid")

    def __repr__(self):
        return f"<Grant {self.code}>"

    class Meta:
        table_name = "grant"


class SiteLog(BaseModel):
    action = IntegerField(null=True)
    desc = CharField(null=True)
    lid = PrimaryKeyField()
    link = CharField(null=True)
    time = DateTimeField(default=datetime.datetime.utcnow)
    uid = ForeignKeyField(db_column="uid", null=True, model=User, field="uid")
    target = ForeignKeyField(db_column="target_uid", null=True, model=User, field="uid")

    def __repr__(self):
        return f"<SiteLog action={self.action}>"

    class Meta:
        table_name = "site_log"


class SiteMetadata(BaseModel):
    key = CharField(null=True)
    value = CharField(null=True)
    xid = PrimaryKeyField()

    def __repr__(self):
        return f"<SiteMetadata {self.key}>"

    class Meta:
        table_name = "site_metadata"


class Sub(BaseModel):
    name = CharField(unique=True, max_length=32)
    nsfw = BooleanField(default=False)
    sid = CharField(primary_key=True, max_length=40)
    sidebar = TextField(default="")
    status = IntegerField(null=True)
    title = CharField(null=True, max_length=50)
    sort = CharField(null=True, max_length=32)
    creation = DateTimeField(default=datetime.datetime.utcnow)
    subscribers = IntegerField(default=1)
    posts = IntegerField(default=0)

    def __repr__(self):
        return f"<Sub {self.name}>"

    class Meta:
        table_name = "sub"

    def get_metadata(self, key):
        """Returns `key` for submetadata or `None` if it does not exist.
        Only works for single keys"""
        try:
            m = SubMetadata.get(
                (SubMetadata.sid == self.sid) & (SubMetadata.key == key)
            )
            return m.value
        except SubMetadata.DoesNotExist:
            return None

    def update_metadata(self, key, value, boolean=True):
        """ Updates `key` for submetadata. Only works for single keys. """
        if boolean:
            if value:
                value = "1"
            elif not value:
                value = "0"
        restr = SubMetadata.get_or_create(sid=self.sid, key=key)[0]
        if restr.value != value:
            restr.value = value
            restr.save()


class SubFlair(BaseModel):
    sid = ForeignKeyField(db_column="sid", null=True, model=Sub, field="sid")
    text = CharField(null=True)
    xid = PrimaryKeyField()

    def __repr__(self):
        return f"<SubFlair {self.text}>"

    class Meta:
        table_name = "sub_flair"


class SubRule(BaseModel):
    sid = ForeignKeyField(db_column="sid", null=True, model=Sub, field="sid")
    text = CharField(null=True)
    rid = PrimaryKeyField()

    def __repr__(self):
        return f"<SubRule {self.text}>"

    class Meta:
        table_name = "sub_rule"


class SubLog(BaseModel):
    action = IntegerField(null=True)
    desc = CharField(null=True)
    lid = PrimaryKeyField()
    link = CharField(null=True)  # link or extra description depending on action
    sid = ForeignKeyField(db_column="sid", null=True, model=Sub, field="sid")
    uid = ForeignKeyField(db_column="uid", null=True, model=User, field="uid")
    target = ForeignKeyField(db_column="target_uid", null=True, model=User, field="uid")
    admin = BooleanField(
        default=False
    )  # True if action was performed by an admin override.
    time = DateTimeField(default=datetime.datetime.utcnow)

    def __repr__(self):
        return f"<SubLog action={self.action}>"

    class Meta:
        table_name = "sub_log"


class SubMetadata(BaseModel):
    key = CharField(null=True)
    sid = ForeignKeyField(db_column="sid", null=True, model=Sub, field="sid")
    value = CharField(null=True)
    xid = PrimaryKeyField()

    def __repr__(self):
        return f"<SubMetadata {self.key}>"

    class Meta:
        table_name = "sub_metadata"


class SubPost(BaseModel):
    content = TextField(null=True)
    deleted = IntegerField(
        default=0
    )  # 1=self delete, 2=mod delete, 3=admin delete, 0=not deleted
    distinguish = IntegerField(null=True)  # 1=mod, 2=admin, 0 or null = normal
    link = CharField(null=True)
    nsfw = BooleanField(null=True)
    pid = PrimaryKeyField()
    posted = DateTimeField(default=datetime.datetime.utcnow)
    edited = DateTimeField(null=True)
    ptype = IntegerField(null=True)  # 1=text, 2=link, 3=poll

    score = IntegerField(default=1)  # XXX: Deprecated
    upvotes = IntegerField(default=0)
    downvotes = IntegerField(default=0)

    sid = ForeignKeyField(db_column="sid", model=Sub, field="sid")
    thumbnail = CharField(null=True)
    title = CharField()
    comments = IntegerField()
    uid = ForeignKeyField(db_column="uid", model=User, field="uid", backref="posts")
    flair = CharField(null=True, max_length=25)

    def __repr__(self):
        return f'<SubPost "{self.title[:20]}">'

    def is_title_editable(self):
        delta = datetime.timedelta(seconds=config.site.title_edit_timeout)
        return (
            datetime.datetime.utcnow() - self.posted.replace(tzinfo=None)
        ) > delta  # noqa

    class Meta:
        table_name = "sub_post"


class SubPostPollOption(BaseModel):
    """ List of options for a poll """

    pid = ForeignKeyField(db_column="pid", model=SubPost, field="pid")
    text = CharField()

    def __repr__(self):
        return f'<SubPostPollOption "{self.text[:20]}">'

    class Meta:
        table_name = "sub_post_poll_option"


class SubPostPollVote(BaseModel):
    """ List of options for a poll """

    pid = ForeignKeyField(db_column="pid", model=SubPost, field="pid")
    uid = ForeignKeyField(db_column="uid", model=User)
    vid = ForeignKeyField(db_column="vid", model=SubPostPollOption, backref="votes")

    def __repr__(self):
        return "<SubPostPollVote>"

    class Meta:
        table_name = "sub_post_poll_vote"


class SubPostComment(BaseModel):
    cid = CharField(primary_key=True, max_length=40)
    content = TextField(null=True)
    lastedit = DateTimeField(null=True)
    parentcid = ForeignKeyField(
        db_column="parentcid", null=True, model="self", field="cid"
    )
    pid = ForeignKeyField(db_column="pid", null=True, model=SubPost, field="pid")
    score = IntegerField(null=True)
    upvotes = IntegerField(default=0)
    downvotes = IntegerField(default=0)
    best_score = FloatField(null=True)
    views = IntegerField(default=0)

    # status:
    #   null or 0: Either not deleted, or reinstated.
    #   1:         The user removed it themselves; still visible to mods, admins.
    #   2:         A mod removed it; still visible to mods, admins and the user.
    #   3:         An admin removed it; still visible to mods, admins and the user.
    status = IntegerField(null=True)
    distinguish = IntegerField(null=True)  # 1=mod, 2=admin, 0 or null = normal
    time = DateTimeField(null=True)
    uid = ForeignKeyField(
        db_column="uid", null=True, model=User, field="uid", backref="comments"
    )

    def __repr__(self):
        return f'<SubPostComment "{self.content[:20]}">'

    class Meta:
        table_name = "sub_post_comment"


class SubPostCommentVote(BaseModel):
    datetime = DateTimeField(null=True, default=datetime.datetime.utcnow)
    cid = CharField(null=True)
    positive = IntegerField(null=True)
    uid = ForeignKeyField(db_column="uid", null=True, model=User, field="uid")
    xid = PrimaryKeyField()

    def __repr__(self):
        return f"<SubPostCommentVote {self.cid}>"

    class Meta:
        table_name = "sub_post_comment_vote"


class SubPostCommentView(BaseModel):
    cid = ForeignKeyField(db_column="cid", model=SubPostComment, field="cid")
    uid = ForeignKeyField(db_column="uid", model=User, field="uid")
    pid = ForeignKeyField(db_column="pid", model=SubPost, field="pid")

    def __repr__(self):
        return f'<SubPostCommentView "{self.cid}">'

    class Meta:
        table_name = "sub_post_comment_view"


class SubPostMetadata(BaseModel):
    key = CharField(null=True)
    pid = ForeignKeyField(db_column="pid", null=True, model=SubPost, field="pid")
    value = CharField(null=True)
    xid = PrimaryKeyField()

    def __repr__(self):
        return f"<SubPostMetadata {self.key}>"

    class Meta:
        table_name = "sub_post_metadata"


class SubPostVote(BaseModel):
    datetime = DateTimeField(null=True, default=datetime.datetime.utcnow)
    pid = ForeignKeyField(
        db_column="pid", null=True, model=SubPost, field="pid", backref="votes"
    )
    positive = IntegerField(null=True)
    uid = ForeignKeyField(db_column="uid", null=True, model=User, field="uid")
    xid = PrimaryKeyField()

    def __repr__(self):
        return f"<SubPostVote {self.positive}>"

    class Meta:
        table_name = "sub_post_vote"


class SubStylesheet(BaseModel):
    content = TextField(null=True)
    source = TextField()
    sid = ForeignKeyField(db_column="sid", null=True, model=Sub, field="sid")
    xid = PrimaryKeyField()

    def __repr__(self):
        return f'<SubStylesheet "{self.source[:20]}">'

    class Meta:
        table_name = "sub_stylesheet"


class SubSubscriber(BaseModel):
    """ Stores subscribed and blocked subs """

    order = IntegerField(null=True)
    sid = ForeignKeyField(db_column="sid", null=True, model=Sub, field="sid")
    # status is 1 for subscribed, 2 for blocked and 4 for saved (displayed in the top bar)
    status = IntegerField(null=True)
    time = DateTimeField(default=datetime.datetime.utcnow)
    uid = ForeignKeyField(db_column="uid", null=True, model=User, field="uid")
    xid = PrimaryKeyField()

    def __repr__(self):
        return f"<SubSubscriber {self.status}>"

    class Meta:
        table_name = "sub_subscriber"


class Token(BaseModel):
    _scopes = TextField(null=True)
    access_token = CharField(null=True, unique=True, max_length=100)
    client = ForeignKeyField(db_column="client_id", model=Client, field="client")
    expires = DateTimeField(null=True)
    refresh_token = CharField(null=True, unique=True, max_length=100)
    token_type = CharField(null=True, max_length=40)
    user = ForeignKeyField(db_column="user_id", null=True, model=User, field="uid")

    def __repr__(self):
        return f"<Token {self.token_type}>"

    class Meta:
        table_name = "token"


class UserMetadata(BaseModel):
    key = CharField(null=True)
    uid = ForeignKeyField(db_column="uid", null=True, model=User, field="uid")
    value = CharField(null=True)
    xid = PrimaryKeyField()

    def __repr__(self):
        return f"<UserMetadata {self.key}>"

    class Meta:
        table_name = "user_metadata"


class Badge(BaseModel):
    bid = PrimaryKeyField()
    # supercalifragilisticexpialidocious == 34
    name = CharField(unique=True, max_length=34)
    alt = CharField(max_length=255)
    icon = CharField()
    score = IntegerField()
    rank = IntegerField()
    trigger = CharField(null=True)

    def __getitem__(self, key):
        tmp = self.__dict__.get(key)
        if key == "icon":
            tmp = file_url(tmp)
        return tmp

    def icon_url(self):
        return file_url(self.icon)


class UserAuthSource(IntEnum):
    """Where authentication is done.  Value for the 'auth_source' key in
    UserMetadata."""

    LOCAL = 0
    KEYCLOAK = 1


class UserSaved(BaseModel):
    pid = IntegerField(null=True)
    uid = ForeignKeyField(db_column="uid", null=True, model=User, field="uid")
    xid = PrimaryKeyField()

    def __repr__(self):
        return f"<UserSaved {self.uid}>"

    class Meta:
        table_name = "user_saved"


class UserUploads(BaseModel):
    xid = PrimaryKeyField()
    pid = ForeignKeyField(db_column="pid", null=True, model=SubPost, field="pid")
    uid = ForeignKeyField(db_column="uid", null=True, model=User, field="uid")
    fileid = CharField(null=True)
    thumbnail = CharField(null=True)
    status = IntegerField()

    def __repr__(self):
        return f"<UserUploads {self.fileid}>"

    class Meta:
        table_name = "user_uploads"


class SubUploads(BaseModel):
    sid = ForeignKeyField(db_column="sid", model=Sub, field="sid")
    fileid = CharField()
    thumbnail = CharField()
    name = CharField()
    size = IntegerField()

    def __repr__(self):
        return f"<SubUploads {self.fileid}>"

    class Meta:
        table_name = "sub_uploads"


class SubPostReport(BaseModel):
    pid = ForeignKeyField(db_column="pid", model=SubPost, field="pid")
    uid = ForeignKeyField(db_column="uid", model=User, field="uid")
    datetime = DateTimeField(default=datetime.datetime.now)
    reason = CharField(max_length=128)
    open = BooleanField(default=True)
    send_to_admin = BooleanField(default=True)

    def __repr__(self):
        return f'<SubPostReport "{self.reason[:20]}">'

    class Meta:
        table_name = "sub_post_report"


class PostReportLog(BaseModel):
    rid = ForeignKeyField(db_column="id", model=SubPostReport, field="id")
    action = IntegerField(null=True)
    desc = CharField(null=True)
    lid = PrimaryKeyField()
    link = CharField(null=True)
    time = DateTimeField(default=datetime.datetime.utcnow)
    uid = ForeignKeyField(db_column="uid", null=True, model=User, field="uid")
    target = ForeignKeyField(db_column="target_uid", null=True, model=User, field="uid")

    def __repr__(self):
        return f"<PostReportLog action={self.action}>"

    class Meta:
        table_name = "post_report_log"


class SubPostCommentReport(BaseModel):
    cid = ForeignKeyField(db_column="cid", model=SubPostComment, field="cid")
    uid = ForeignKeyField(db_column="uid", model=User, field="uid")
    datetime = DateTimeField(default=datetime.datetime.now)
    reason = CharField(max_length=128)
    open = BooleanField(default=True)
    send_to_admin = BooleanField(default=True)

    def __repr__(self):
        return f'<SubPostCommentReport "{self.reason[:20]}">'

    class Meta:
        table_name = "sub_post_comment_report"


class CommentReportLog(BaseModel):
    rid = ForeignKeyField(db_column="id", model=SubPostCommentReport, field="id")
    action = IntegerField(null=True)
    desc = CharField(null=True)
    lid = PrimaryKeyField()
    link = CharField(null=True)
    time = DateTimeField(default=datetime.datetime.utcnow)
    uid = ForeignKeyField(db_column="uid", null=True, model=User, field="uid")
    target = ForeignKeyField(db_column="target_uid", null=True, model=User, field="uid")

    def __repr__(self):
        return f"<CommentReportLog action={self.action}>"

    class Meta:
        table_name = "comment_report_log"


class SubPostCommentHistory(BaseModel):
    cid = ForeignKeyField(db_column="cid", model=SubPostComment, field="cid")
    datetime = DateTimeField(default=datetime.datetime.now)
    content = TextField(null=True)

    def __repr__(self):
        return f'<SubPostCommentHistory "{self.content[:20]}">'

    class Meta:
        table_name = "sub_post_comment_history"


class SubPostContentHistory(BaseModel):
    pid = ForeignKeyField(db_column="pid", model=SubPost, field="pid")
    datetime = DateTimeField(default=datetime.datetime.now)
    content = TextField(null=True)

    def __repr__(self):
        return f'<SubPostContentHistory "{self.content[:20]}">'

    class Meta:
        table_name = "sub_post_content_history"


class SubPostTitleHistory(BaseModel):
    pid = ForeignKeyField(db_column="pid", model=SubPost, field="pid")
    datetime = DateTimeField(default=datetime.datetime.now)
    title = TextField(null=True)

    def __repr__(self):
        return f'<SubPostContentHistory "{self.content[:20]}">'

    class Meta:
        table_name = "sub_post_title_history"


class UserMessageBlock(BaseModel):
    uid = ForeignKeyField(db_column="uid", model=User, field="uid")
    target = CharField(max_length=40)
    date = DateTimeField(default=datetime.datetime.now)

    def __repr__(self):
        return f'<UserMessageBlock "{self.id}">'

    class Meta:
        table_name = "user_message_block"


class UserContentBlockMethod(IntEnum):
    """Ways to block content for users.
    Value of the 'method' field in UserContentBlock."""

    HIDE = 0
    BLUR = 1


class UserContentBlock(BaseModel):
    uid = ForeignKeyField(db_column="uid", model=User, field="uid")
    target = CharField(max_length=40)
    date = DateTimeField(default=datetime.datetime.now)
    method = IntegerField()  # 0=hide, 1=blur

    def __repr__(self):
        return f'<UserContentBlock "{self.id}">'

    class Meta:
        table_name = "user_content_block"


class APIToken(BaseModel):
    user = ForeignKeyField(db_column="uid", model=User, field="uid")
    token = CharField(unique=True)
    can_post = BooleanField()
    can_mod = BooleanField()
    can_message = BooleanField()
    can_upload = BooleanField()
    is_active = BooleanField(default=True)
    is_ip_restricted = BooleanField(default=False)

    def __repr__(self):
        return f"<APIToken {self.token}>"

    class Meta:
        table_name = "api_token"


class APITokenSettings(BaseModel):
    """ API Token settings. Mainly used for IP whitelisting """

    token = ForeignKeyField(model=APIToken, field="id")
    key = CharField()
    value = CharField()

    def __repr__(self):
        return f"<APITokenSettings {self.key}>"

    class Meta:
        table_name = "api_token_settings"


class SubMod(BaseModel):
    user = ForeignKeyField(db_column="uid", model=User, field="uid")
    sub = ForeignKeyField(db_column="sid", model=Sub, field="sid")
    # Power level: 0=owner, 1=mod, 2=janitor
    power_level = IntegerField()

    invite = BooleanField(default=False)  # if True, mod is invited and not effective

    def __repr__(self):
        return f"<SubMod power_level={self.power_level}>"

    class Meta:
        table_name = "sub_mod"


class SubBan(BaseModel):
    user = ForeignKeyField(db_column="uid", model=User, field="uid")
    sub = ForeignKeyField(db_column="sid", model=Sub, field="sid")

    created = DateTimeField(default=datetime.datetime.utcnow)
    reason = CharField(max_length=128)
    expires = DateTimeField(null=True)
    effective = BooleanField(default=True)

    created_by = ForeignKeyField(db_column="created_by_id", model=User, field="uid")

    def __repr__(self):
        return f'<SubBan "{self.reason[:20]}">'

    class Meta:
        table_name = "sub_ban"


class SubUserFlairChoice(BaseModel):
    """
    Stores possible user flair choces for a sub
    """

    sub = ForeignKeyField(db_column="sid", model=Sub, field="sid")
    flair = CharField(null=False, max_length=25)

    class Meta:
        table_name = "sub_user_flair_choice"


class SubUserFlair(BaseModel):
    """
    Stores flairs assigned to users in a Sub
    """

    user = ForeignKeyField(db_column="uid", model=User, field="uid")
    sub = ForeignKeyField(db_column="sid", model=Sub, field="sid")

    flair = CharField(null=False, max_length=25)

    flair_choice = ForeignKeyField(model=SubUserFlairChoice, null=True)

    class Meta:
        table_name = "sub_user_flair"


class InviteCode(BaseModel):
    user = ForeignKeyField(db_column="uid", model=User, field="uid")

    code = CharField(max_length=64)

    created = DateTimeField(default=datetime.datetime.utcnow)
    expires = DateTimeField(null=True)
    uses = IntegerField(default=0)
    max_uses = IntegerField()

    @classmethod
    def get_valid(cls, invite_code):
        """Returns a valid invite code
        @raise InviteCode.DoesNotExist
        """

        return (
            InviteCode.select()
            .join(User)
            .where(InviteCode.code == invite_code)
            .where(
                (
                    InviteCode.expires.is_null()
                    | (InviteCode.expires > datetime.datetime.utcnow())
                )
                & (User.status == UserStatus.OK)
            )
            .where(InviteCode.max_uses > InviteCode.uses)
            .get()
        )

    def __repr__(self):
        return f"<InviteCode {self.code}>"

    class Meta:
        table_name = "invite_code"


class Wiki(BaseModel):
    is_global = BooleanField()
    sub = ForeignKeyField(db_column="sid", model=Sub, field="sid", null=True)

    slug = CharField(max_length=128)
    title = CharField(max_length=255)
    content = TextField()

    created = DateTimeField(default=datetime.datetime.utcnow)
    updated = DateTimeField(default=datetime.datetime.utcnow)


class Notification(BaseModel):
    """ Holds user notifications. """

    # Notification type. Can be one of:
    # - POST_REPLY, COMMENT_REPLY
    # - POST_MENTION, COMMENT_MENTION

    # These were used in old notifications, but are now sent as messages.
    # - SUB_BAN, SUB_UNBAN
    # - MOD_INVITE, MOD_INVITE_JANITOR, MOD_INVITE_OWNER
    # - POST_DELETE, POST_UNDELETE
    type = CharField()

    sub = ForeignKeyField(db_column="sid", model=Sub, field="sid", null=True)
    # Post the notification is referencing, if it applies
    post = ForeignKeyField(db_column="pid", model=SubPost, field="pid", null=True)
    # Comment the notification is referring, if it applies
    comment = ForeignKeyField(
        db_column="cid", model=SubPostComment, field="cid", null=True
    )
    # User that triggered the action. If null the action is triggered by the system
    sender = ForeignKeyField(db_column="sentby", model=User, field="uid", null=True)

    target = ForeignKeyField(db_column="receivedby", model=User, field="uid", null=True)
    read = DateTimeField(null=True)
    # For future custom text notifications sent by admins (badge notifications?)015_notifications
    content = TextField(null=True)

    created = DateTimeField(default=datetime.datetime.utcnow)

    def __repr__(self):
        return f'<Notification target="{self.user}" type="{self.type}" >'


class MessageType(IntEnum):
    """Types of private messages.
    Value of the 'mtype' field in Message."""

    USER_TO_USER = 100
    USER_TO_MODS = 101
    MOD_TO_USER_AS_USER = 102
    MOD_TO_USER_AS_MOD = 103
    MOD_DISCUSSION = 104
    USER_NOTIFICATION = 105
    MOD_NOTIFICATION = 106


class MessageMailbox(IntEnum):
    """Mailboxes for private messages."""

    INBOX = 200
    SENT = 201
    SAVED = 202
    ARCHIVED = 203  # Modmail only.
    TRASH = 204
    DELETED = 205
    PENDING = 206  # Modmail only.


class MessageThread(BaseModel):
    """Fields shared by all messages in a private message thread."""

    mtid = PrimaryKeyField()
    replies = IntegerField(default=0)
    subject = CharField()
    # Relevant for modmail messages, otherwise NULL.
    sub = ForeignKeyField(db_column="sid", null=True, model=Sub, field="sid")

    def __repr__(self):
        return f'<MessageThread "{self.mtid}"'

    class Meta:
        table_name = "message_thread"


class Message(BaseModel):
    mid = PrimaryKeyField()
    thread = ForeignKeyField(db_column="mtid", model=MessageThread, field="mtid")
    content = TextField(null=True)
    mtype = IntegerField(null=True)
    posted = DateTimeField(null=True)
    # True if this message is the first in its thread.
    first = BooleanField(default=False)

    # Relevant for messages to individual users, otherwise NULL.
    receivedby = ForeignKeyField(
        db_column="receivedby", null=True, model=User, field="uid"
    )

    # The user who created the message, even for modmails.
    sentby = ForeignKeyField(
        db_column="sentby",
        null=True,
        model=User,
        backref="user_sentby_set",
        field="uid",
    )

    def __repr__(self):
        return f'<Message "{self.mid}"'

    class Meta:
        table_name = "message"


class UserUnreadMessage(BaseModel):
    uid = ForeignKeyField(db_column="uid", model=User, field="uid")
    mid = ForeignKeyField(db_column="mid", model=Message, field="mid")

    def __repr__(self):
        return f'<UserUnreadMessage "{self.uid}/{self.mid}"'

    class Meta:
        table_name = "user_unread_message"


class UserMessageMailbox(BaseModel):
    uid = ForeignKeyField(db_column="uid", model=User, field="uid")
    mid = ForeignKeyField(db_column="mid", model=Message, field="mid")
    mailbox = IntegerField(default=MessageMailbox.INBOX)

    def __repr__(self):
        return f'<UserMessageMailbox "{self.uid}/{self.mid}"'

    class Meta:
        table_name = "user_message_mailbox"


class SubMessageMailbox(BaseModel):
    thread = ForeignKeyField(db_column="mtid", model=MessageThread, field="mtid")
    mailbox = IntegerField(default=MessageMailbox.INBOX)
    highlighted = BooleanField(default=False)

    def __repr__(self):
        return f'<SubMessageMailbox "{self.id}"'

    class Meta:
        table_name = "sub_message_mailbox"


class SubMessageLogAction(IntEnum):
    CHANGE_MAILBOX = 1
    HIGHLIGHT = 2


class SubMessageLog(BaseModel):
    action = IntegerField(default=SubMessageLogAction.CHANGE_MAILBOX)
    thread = ForeignKeyField(db_column="mtid", model=MessageThread, field="mtid")
    uid = ForeignKeyField(db_column="uid", model=User, field="uid")
    desc = CharField(null=True)
    updated = DateTimeField(default=datetime.datetime.utcnow)

    def __repr__(self):
        return f'<SubMessageLog "{self.id}"'

    class Meta:
        table_name = "sub_message_log"
