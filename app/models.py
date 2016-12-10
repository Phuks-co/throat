""" Database table definitions """

import datetime
import uuid
from urllib.parse import urlparse
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean
from sqlalchemy.ext.hybrid import hybrid_property
from flask_sqlalchemy import SQLAlchemy
from flask_login import current_user
import bcrypt
from .caching import CacheableMixin, query_callable, regions


db = SQLAlchemy()


class User(db.Model, CacheableMixin):
    """ Basic user data (Used for login or password recovery) """
    cache_label = "default"  # region's label to use
    cache_regions = regions  # regions to store cache
    cache_pk = 'uid'
    # Query handeling dogpile caching
    query_class = query_callable(regions)

    uid = Column(String(40), primary_key=True)
    name = Column(String(64), unique=True)
    email = Column(String(128))
    # In case we migrate to a different cipher for passwords
    # 1 = bcrypt
    crypto = Column(Integer)
    password = Column(String(255))
    # Account status
    # 0 = OK; 1 = banned; 2 = shadowbanned?; 3 = sent to oblivion?
    status = Column(Integer)
    joindate = Column(DateTime)
    subscribed = db.relationship('SubSubscriber', backref='user',
                                 lazy='dynamic')
    posts = db.relationship('SubPost', backref='_user', lazy='joined')

    properties = db.relationship('UserMetadata',
                                 backref='user', lazy='dynamic')
    comments = db.relationship('SubPostComment', backref='user',
                               lazy='dynamic')

    def __init__(self, username, email, password):
        self.uid = str(uuid.uuid4())
        self.name = username
        self.email = email
        self.crypto = 1
        self.status = 0
        self.joindate = datetime.datetime.utcnow()
        self.setPassword(password)

    def setPassword(self, password):
        password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        if isinstance(password, bytes):
            self.password = password.decode('utf-8')
        else:
            self.password = password

    def __repr__(self):
        return '<User %r>' % self.name

    @hybrid_property
    def showLinksNewTab(self):
        """ Returns true user selects to open links in a new window """
        x = UserMetadata.cache.filter(key='exlinks', uid=self.uid)
        try:
            x = next(x)
            return bool(x.value)
        except StopIteration:
            return False

    @hybrid_property
    def showStyles(self):
        """ Returns true user selects to see sustom sub stylesheets """
        x = UserMetadata.cache.filter(key='styles', uid=self.uid)
        try:
            x = next(x)
            return bool(x.value)
        except StopIteration:
            return False


class UserMetadata(db.Model, CacheableMixin):
    """ User metadata. Here we store badges, admin status, etc. """
    cache_label = "default"  # region's label to use
    cache_regions = regions  # regions to store cache
    # Query handeling dogpile caching
    cache_pk = 'xid'
    query_class = query_callable(regions)

    xid = Column(Integer, primary_key=True)
    uid = Column(String(40), db.ForeignKey('user.uid'))  # Subverse id
    key = Column(String(255))  # Metadata key
    value = Column(String(255))

    def __init__(self, uid, key, value):
        self.uid = uid
        self.key = key
        self.value = value

    @hybrid_property
    def getBadgeClass(self):
        """ Returns the badge's css class """
        if self.key != "badge":
            return False
        x = UserBadge.query.get(self.value)
        return str(x.badge)

    @hybrid_property
    def getBadgeName(self):
        """ Returns the badge's name """
        if self.key != "badge":
            return False
        x = UserBadge.query.get(self.value)
        return str(x.name)

    @hybrid_property
    def getBadgeText(self):
        """ Returns the badge's hover text """
        if self.key != "badge":
            return False
        x = UserBadge.query.get(self.value)
        return str(x.text)


class UserBadge(db.Model):
    """ Here we store badge definitions """
    cache_label = "default"  # region's label to use
    cache_regions = regions  # regions to store cache
    # Query handeling dogpile caching
    query_class = query_callable(regions)

    bid = Column(String(40), primary_key=True)
    badge = Column(String(255))  # fa-xxx, badge icon id.
    name = Column(String(255))  # Badge name
    # Short text displayed when hovering the badge
    text = Column(String(255))

    def __init__(self, badge, name, text):
        self.bid = str(uuid.uuid4())
        self.badge = badge
        self.name = name
        self.text = text


class Sub(db.Model, CacheableMixin):
    """ Basic sub data """
    cache_label = "default"  # region's label to use
    cache_regions = regions  # regions to store cache
    cache_pk = 'sid'
    # Query handeling dogpile caching
    query_class = query_callable(regions)

    sid = Column(String(40), primary_key=True)  # sub id
    name = Column(String(32), unique=True)  # sub name
    title = Column(String(128))  # sub title/desc

    status = Column(Integer)  # Sub status. 0 = ok; 1 = banned; etc

    sidebar = Column(Text)

    subscribers = db.relationship('SubSubscriber', backref='sub',
                                  lazy='dynamic')
    _posts = db.relationship('SubPost', backref='__sub', lazy='joined')
    __posts = db.relationship('SubPost', backref='_sub', lazy='dynamic')
    properties = db.relationship('SubMetadata', backref='sub', lazy='subquery')
    flairs = db.relationship('SubFlair', backref='sub', lazy='dynamic')
    __stylesheet = db.relationship('SubStylesheet', backref='sub',
                                   lazy='dynamic')

    def __init__(self, name, title):
        self.sid = str(uuid.uuid4())
        self.name = name
        self.sidebar = ''
        self.title = title

    def __repr__(self):
        return '<Sub {0}-{1}>'.format(self.name, self.title)

    @hybrid_property
    def posts(self):
        """ gets posts from sub, replaces the db relationship """
        return SubPost.query.filter_by(sid=self.sid)

    @hybrid_property
    def stylesheet(self):
        """ gets stylesheet from sub, replaces the db relationship """
        return next(SubStylesheet.cache.filter(sid=self.sid))


class SubFlair(db.Model, CacheableMixin):
    """ Stores all the flairs for all da subs """
    cache_label = "default"  # region's label to use
    cache_regions = regions  # regions to store cache
    cache_pk = 'xid'
    query_class = query_callable(regions)

    xid = Column(Integer, primary_key=True)
    sid = Column(String(40), db.ForeignKey('sub.sid'))  # Subverse id
    text = Column(String(64))


class SubMetadata(db.Model, CacheableMixin):
    """ Sub metadata. Here we store if the sub is nsfw, the modlist,
    the founder, etc. """
    cache_label = "default"  # region's label to use
    cache_regions = regions  # regions to store cache
    # Query handeling dogpile caching
    cache_pk = 'xid'
    query_class = query_callable(regions)

    xid = Column(Integer, primary_key=True)
    sid = Column(String(40), db.ForeignKey('sub.sid'))  # Subverse id
    key = Column(String(255))  # Metadata key
    value = Column(String(255))

    def __init__(self, sub, key, value):
        self.sid = sub.sid
        self.key = key
        self.value = value

    @hybrid_property
    def getUsername(self):
        """ Returns username from str """
        x = User.cache.get(self.value)
        return x.name

    @hybrid_property
    def getSubName(self):
        """ Returns the sub's name from str """
        x = Sub.cache.get(self.sid)
        return str(x.name)


class SubSubscriber(db.Model, CacheableMixin):
    """ Stores subscribers for a sub. """
    cache_label = "default"  # region's label to use
    cache_regions = regions  # regions to store cache
    cache_pk = 'xid'
    # Query handeling dogpile caching
    query_class = query_callable(regions)

    # Note: We usually use integer primary keys when we don't need to actually
    # use the primary keys (but we should always define them, because it speeds
    # up queries and stuff), when we have to store an ID we always use uuid4s
    # The only exception is SubPost >_>
    xid = Column(Integer, primary_key=True)
    sid = Column(String(40), db.ForeignKey('sub.sid'))
    uid = Column(String(40), db.ForeignKey('user.uid'))
    status = Column(Integer)  # 1=subscribed 2=blocked 3=custom
    time = Column(DateTime)

    @hybrid_property
    def getSubName(self):
        """ Returns the sub's name from str """
        x = Sub.cache.get(self.sid)
        return str(x.name)


class SubStylesheet(db.Model, CacheableMixin):
    """ Stores sub's custom CSS """
    cache_label = "default"  # region's label to use
    cache_regions = regions  # regions to store cache
    cache_pk = 'xid'
    # Query handeling dogpile caching
    query_class = query_callable(regions)

    xid = Column(Integer, primary_key=True)
    sid = Column(String(40), db.ForeignKey('sub.sid'))  # Subverse id
    content = Column(Text)

    def __init__(self, sub, content):
        self.sid = sub.sid
        self.content = content


class SubPost(db.Model, CacheableMixin):
    """ Represents a post on a sub """
    cache_label = "default"  # region's label to use
    cache_regions = regions  # regions to store cache
    cache_pk = 'pid'
    # Query handeling dogpile caching
    query_class = query_callable(regions)
    pid = Column(Integer, primary_key=True)  # post id
    sid = Column(String(40), db.ForeignKey('sub.sid'))
    uid = Column(String(40), db.ForeignKey('user.uid'))

    # There's a 'sub' field with a reference to the sub and a 'user' one
    # with a refernece to the user that created this post

    title = Column(String(256))  # post title
    link = Column(String(256))  # post target (if it is a link post)
    # post content (if it is a text post)
    content = Column(Text())

    posted = Column(DateTime)

    ptype = Column(Integer)  # Post type. 0=txt; 1=link; etc

    _properties = db.relationship('SubPostMetadata',
                                  backref='post', lazy='subquery')

    comments = db.relationship('SubPostComment', backref='post',
                               lazy='dynamic')

    votes = db.relationship('SubPostVote', backref='post',
                            lazy='subquery')

    def __init__(self, sid):
        self.sid = sid
        self.uid = current_user.get_id()
        self.posted = datetime.datetime.utcnow()

    def is_sticky(self):
        """ Returns True if this post is stickied """
        x = SubMetadata.cache.filter(key='sticky', sid=self.sid,
                                     value=self.pid)
        try:
            x = next(x)
            x = True
        except StopIteration:
            x = False
        return bool(x)

    def voteCount(self):
        """ Returns the post's vote count """
        # db.session.expunge_all()

        votes = SubPostMetadata.cache.filter(key='score', pid=self.pid)
        try:
            votes = next(votes)
        except StopIteration:
            return 1
        return int(votes.value) if votes else 0

    def getComments(self, parent=None):
        """ Returns cached post comments """
        comms = SubPostComment.cache.filter(pid=self.pid, parentcid=parent)
        comms = list(comms)
        return comms

    def getDomain(self):
        """ Gets Domain """
        x = urlparse(self.link)
        return x.netloc

    @hybrid_property
    def sub(self):
        """ Returns post's sub, replaces db relationship """
        return Sub.cache.get(self.sid)

    @hybrid_property
    def user(self):
        """ Returns post creator, replaces db relationship """
        return User.cache.get(self.uid)

    @hybrid_property
    def properties(self):
        """ Returns ALL post metadata. You should not use this >:| """
        return User.cache.filter(pid=self.pid)

    @hybrid_property
    def thumb(self):
        """ Returns thumbnail address for post """
        x = SubPostMetadata.cache.filter(pid=self.pid, key='thumbnail')
        try:
            return next(x).value
        except StopIteration:
            return False

    def isImage(self):
        """ Returns True if link ends with img suffix """
        suffix = ['.png', '.jpg', '.gif', '.tiff', '.bmp']
        return self.link.lower().endswith(tuple(suffix))

    def isAnnouncement(self):
        """ Returns True if post is an announcement """
        ann = SiteMetadata.query.filter_by(key='announcement').first()
        return bool(ann and ann.value == str(self.pid))

    def isPostNSFW(self):
        """ Returns true if the post is marked as NSFW """
        x = SubPostMetadata.cache.filter(key='nsfw', pid=self.pid)
        try:
            x = next(x)
        except StopIteration:
            return False
        return True if x.value == '1' else False


class SubPostMetadata(db.Model, CacheableMixin):
    """ Post metadata. Here we store if it is a sticky post, mod post, tagged
    as nsfw, etc. """
    cache_label = "default"  # region's label to use
    cache_regions = regions  # regions to store cache
    cache_pk = 'xid'
    # Query handeling dogpile caching
    query_class = query_callable(regions)

    xid = Column(Integer, primary_key=True)
    pid = Column(Integer, db.ForeignKey('sub_post.pid'))
    key = Column(String(255))  # Metadata key
    value = Column(String(255))

    def __init__(self, pid, key, value):
        self.pid = pid
        self.key = key
        self.value = value

    def __repr__(self):
        return '<SubPostMetadata ({0}); {1} = {2}>'.format(self.pid, self.key,
                                                           self.value)


class SubPostComment(db.Model, CacheableMixin):
    """ A comment. In a post. """
    cache_label = "default"  # region's label to use
    cache_regions = regions  # regions to store cache
    # Query handeling dogpile caching
    cache_pk = 'cid'
    query_class = query_callable(regions)

    cid = Column(String(64), primary_key=True)
    pid = Column(Integer, db.ForeignKey('sub_post.pid'))
    uid = Column(String(40), db.ForeignKey('user.uid'))
    time = Column(DateTime)
    content = Column(Text())
    # parent comment id
    parentcid = Column(String(40), db.ForeignKey('sub_post_comment.cid'),
                       nullable=True)
    children = db.relationship("SubPostComment",
                               backref=db.backref("parent", remote_side=cid))

    def __init__(self):
        self.cid = str(uuid.uuid4())

    @hybrid_property
    def getUname(self):
        """ Returns username from str """
        x = User.query.filter_by(uid=self.uid).first()
        return str(x.name)


class SubPostVote(db.Model, CacheableMixin):
    """ Up/Downvotes in a post. """
    cache_label = "default"  # region's label to use
    cache_regions = regions  # regions to store cache
    cache_pk = 'xid'
    # Query handeling dogpile caching
    query_class = query_callable(regions)

    xid = Column(Integer, primary_key=True)
    pid = Column(Integer, db.ForeignKey('sub_post.pid'))
    uid = Column(String(40), db.ForeignKey('user.uid'))
    positive = Column(Boolean)

    @hybrid_property
    def getUsername(self):
        """ Returns username from str """
        x = User.cache.get(self.uid)
        return x.name


class Message(db.Model, CacheableMixin):
    """ Represents a post on a sub """
    cache_label = "default"  # region's label to use
    cache_regions = regions  # regions to store cache
    cache_pk = 'mid'
    # Query handeling dogpile caching
    query_class = query_callable(regions)

    mid = Column(Integer, primary_key=True)  # msg id
    sentby = Column(String(40), db.ForeignKey('user.uid'))
    receivedby = Column(String(40), db.ForeignKey('user.uid'))

    subject = Column(String(128))  # msg subject
    content = Column(Text())  # msg content

    posted = Column(DateTime)  # sent
    read = Column(DateTime)  # todo markasread time

    mtype = Column(Integer)  # msg type. 0=pm; 1=mod; 2=username mention; etc
    mlink = Column(String(128)) # link to be included

    def __repr__(self):
        return '<Messages {0}>'.format(self.subject)

    @hybrid_property
    def getMsgSentBy(self):
        """ Returns this message's sender. """
        x = User.query.filter_by(uid=self.sentby).first()
        return str(x.name)

    @hybrid_property
    def getMsgRecBy(self):
        """ Returns this message's recipient """
        x = User.query.filter_by(uid=self.receivedby).first()
        return str(x.name)


class SiteMetadata(db.Model):
    """ Site-wide configs """
    cache_label = "default"  # region's label to use
    cache_regions = regions  # regions to store cache
    # Query handeling dogpile caching
    query_class = query_callable(regions)

    xid = Column(Integer, primary_key=True)
    key = Column(String(255))  # Metadata key
    value = Column(String(255))


class SubLog(db.Model):
    """ Sub modlogs """
    cache_label = "default"  # region's label to use
    cache_regions = regions  # regions to store cache
    # Query handeling dogpile caching
    query_class = query_callable(regions)

    lid = Column(Integer, primary_key=True)  # log id
    sid = Column(String(40), db.ForeignKey('sub.sid'))  # sub.sid
    time = Column(DateTime)
    # 1 = deletion, 2 = user ban, 3 = flair, 4 = modedit, 5 = comment, 6 = mods
    action = Column(Integer)
    desc = Column(String(255))  # description
    link = Column(String(255))

    def __init__(self, sid):
        self.sid = sid
        self.time = datetime.datetime.utcnow()


class SiteLog(db.Model):
    """ Sub modlogs """
    cache_label = "default"  # region's label to use
    cache_regions = regions  # regions to store cache
    # Query handeling dogpile caching
    query_class = query_callable(regions)

    lid = Column(Integer, primary_key=True)  # log id
    time = Column(DateTime)
    # 1 deletion, 2 users, 3 ann, 4 subs, 5 mods/admins
    action = Column(Integer)
    desc = Column(String(255))  # description
    link = Column(String(255))
