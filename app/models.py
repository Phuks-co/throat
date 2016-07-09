""" Database table definitions """

import datetime
import uuid
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean
from sqlalchemy.ext.hybrid import hybrid_property
from flask_sqlalchemy import SQLAlchemy
import bcrypt
from tld import get_tld

db = SQLAlchemy()


class User(db.Model):
    """ Basic user data (Used for login or password recovery) """
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
    posts = db.relationship('SubPost', backref='user', lazy='joined')

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
        x = self.properties.filter_by(key='exlinks').first()
        if x:
            return True if x.value == '1' else False
        else:
            return False

    @hybrid_property
    def showStyles(self):
        """ Returns true user selects to see sustom sub stylesheets """
        x = self.properties.filter_by(key='styles').first()
        if x:
            return True if x.value == '1' else False
        else:
            return False

    @hybrid_property
    def showNSFW(self):
        """ Returns true user selects to see NSFW posts """
        x = self.properties.filter_by(key='nsfw').first()
        if x:
            return True if x.value == '1' else False
        else:
            return False

class UserMetadata(db.Model):
    """ User metadata. Here we store badges, admin status, etc. """
    xid = Column(Integer, primary_key=True)
    uid = Column(String(40), db.ForeignKey('user.uid'))  # Subverse id
    key = Column(String(255))  # Metadata key
    value = Column(String(255))

    @hybrid_property
    def getBadgeClass(self):
        """ Returns the badge's css class """
        if self.key != "badge":
            return False
        x = UserBadge.query.filter_by(bid=self.value).first()
        return str(x.badge)

    @hybrid_property
    def getBadgeName(self):
        """ Returns the badge's name """
        if self.key != "badge":
            return False
        x = UserBadge.query.filter_by(bid=self.value).first()
        return str(x.name)

    @hybrid_property
    def getBadgeText(self):
        """ Returns the badge's hover text """
        if self.key != "badge":
            return False
        x = UserBadge.query.filter_by(bid=self.value).first()
        return str(x.text)


class UserBadge(db.Model):
    """ Here we store badge definitions """
    bid = Column(String(40), primary_key=True)
    badge = Column(String(255))  # fa-xxx, badge icon id.
    name = Column(String(255))  # Badge name
    # Short text displayed when hovering the badge
    text = Column(String(255, collation='utf8_bin'))

    def __init__(self, badge, name, text):
        self.bid = str(uuid.uuid4())
        self.badge = badge
        self.name = name
        self.text = text


class Sub(db.Model):
    """ Basic sub data """
    sid = Column(String(40), primary_key=True)  # sub id
    name = Column(String(32), unique=True)  # sub name
    title = Column(String(128, collation='utf8_bin'))  # sub title/desc

    status = Column(Integer)  # Sub status. 0 = ok; 1 = banned; etc

    subscribers = db.relationship('SubSubscriber', backref='sub',
                                  lazy='dynamic')
    posts = db.relationship('SubPost', backref='sub', lazy='dynamic')
    properties = db.relationship('SubMetadata', backref='sub', lazy='dynamic')
    stylesheet = db.relationship('SubStylesheet', backref='sub',
                                 lazy='dynamic')

    def __init__(self, name, title):
        self.sid = str(uuid.uuid4())
        self.name = name
        self.title = title

    def __repr__(self):
        return '<Sub {0}-{1}>'.format(self.name, self.title)

    @hybrid_property
    def getSubPostCount(self):
        """ Returns the sub's post count """
        x = self.posts.filter_by(sid=self.sid).count()
        return str(x)

    @hybrid_property
    def getModCount(self):
        """ Returns the sub's mod count metadata """
        x = self.properties.filter_by(key='mod2').count()
        return str(x)

    @hybrid_property
    def isNSFW(self):
        """ Returns true if the sub is marked as NSFW """
        x = self.properties.filter_by(key='nsfw').first()
        return True if x.value == '1' else False


class SubMetadata(db.Model):
    """ Sub metadata. Here we store if the sub is nsfw, the modlist,
    the founder, etc. """
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
        x = User.query.filter_by(uid=self.value).first()
        return str(x.name)

    @hybrid_property
    def getSubName(self):
        """ Returns the sub's name from str """
        x = Sub.query.filter_by(sid=self.sid).first()
        return str(x.name)

class SubSubscriber(db.Model):
    """ Stores subscribers for a sub. """
    # Note: We usually use integer primary keys when we don't need to actually
    # use the primary keys (but we should always define them, because it speeds
    # up queries and stuff), when we have to store an ID we always use uuid4s
    # The only exception is SubPost >_>
    xid = Column(Integer, primary_key=True)
    sid = Column(String(40), db.ForeignKey('sub.sid'))
    uid = Column(String(40), db.ForeignKey('user.uid'))
    status = Column(Integer) # 1=subscribed 2=blocked 3=custom
    time = Column(DateTime)


class SubStylesheet(db.Model):
    """ Stores sub's custom CSS """
    xid = Column(Integer, primary_key=True)
    sid = Column(String(40), db.ForeignKey('sub.sid'))  # Subverse id
    content = Column(Text)

    def __init__(self, sub, content):
        self.sid = sub.sid
        self.content = content


class SubPost(db.Model):
    """ Represents a post on a sub """
    pid = Column(Integer, primary_key=True)  # post id
    sid = Column(String(40), db.ForeignKey('sub.sid'))
    uid = Column(String(40), db.ForeignKey('user.uid'))

    # There's a 'sub' field with a reference to the sub and a 'user' one
    # with a refernece to the user that created this post

    title = Column(String(128, collation='utf8_bin'))  # post title
    link = Column(String(128))  # post target (if it is a link post)
    # post content (if it is a text post)
    content = Column(Text(collation='utf8_bin'))

    posted = Column(DateTime)

    ptype = Column(Integer)  # Post type. 0=txt; 1=link; etc

    properties = db.relationship('SubPostMetadata',
                                 backref='post', lazy='dynamic')

    comments = db.relationship('SubPostComment', backref='post',
                               lazy='dynamic')

    votes = db.relationship('SubPostVote', backref='post',
                            lazy='subquery')

    def __repr__(self):
        return '<SubPost {0} (In Sub{1})>'.format(self.title, self.sid)

    @hybrid_property
    def voteCount(self):
        """ Returns the post's vote count """
        count = 0
        for vote in self.votes:
            if vote.positive:
                count += 1
            else:
                count -= 1
        return count + 1

    def getDomain(self):
        """ Gets Domain """
        x = get_tld(self.link)
        return x

    def isImage(self):
        """ Returns True if link ends with img suffix """
        suffix = ['.png', '.jpg', '.gif', '.tiff', '.bmp']
        return self.link.lower().endswith(tuple(suffix))

    def isPostNSFW(self):
        """ Returns true if the post is marked as NSFW """
        x = self.properties.filter_by(key='nsfw').first()
        if not x:
            return False
        return True if x.value == '1' else False


class SubPostMetadata(db.Model):
    """ Post metadata. Here we store if it is a sticky post, mod post, tagged
    as nsfw, etc. """
    xid = Column(Integer, primary_key=True)
    pid = Column(Integer, db.ForeignKey('sub_post.pid'))
    key = Column(String(255))  # Metadata key
    value = Column(String(255))

    def __init__(self, pid, key, value):
        self.pid = pid
        self.key = key
        self.value = value


class SubPostComment(db.Model):
    """ A comment. In a post. """
    cid = Column(String(64), primary_key=True)
    pid = Column(Integer, db.ForeignKey('sub_post.pid'))
    uid = Column(String(40), db.ForeignKey('user.uid'))
    time = Column(DateTime)
    content = Column(Text(collation='utf8_bin'))
    # parent comment id
    parentcid = Column(String(40), db.ForeignKey('sub_post_comment.cid'),
                       nullable=True)
    children = db.relationship("SubPostComment",
                               backref=db.backref("parent", remote_side=cid))

    def __init__(self):
        self.cid = str(uuid.uuid4())


class SubPostVote(db.Model):
    """ Up/Downvotes in a post. """
    xid = Column(Integer, primary_key=True)
    pid = Column(Integer, db.ForeignKey('sub_post.pid'))
    uid = Column(String(40), db.ForeignKey('user.uid'))
    positive = Column(Boolean)


class Message(db.Model):
    """ Represents a post on a sub """
    mid = Column(Integer, primary_key=True)  # msg id
    sentby = Column(String(40), db.ForeignKey('user.uid'))
    receivedby = Column(String(40), db.ForeignKey('user.uid'))

    subject = Column(String(128))  # msg subject
    content = Column(Text(collation='utf8_bin'))  # msg content

    posted = Column(DateTime)  # sent
    read = Column(DateTime)  # todo markasread time

    mtype = Column(Integer)  # msg type. 0=pm; 1=mod; 2=username mention; etc

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
    xid = Column(Integer, primary_key=True)
    key = Column(String(255))  # Metadata key
    value = Column(String(255))
