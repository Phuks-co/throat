""" Database table definitions """

import datetime
import uuid
from sqlalchemy import Column, Integer, String, Text, DateTime
from flask_sqlalchemy import SQLAlchemy
import bcrypt

db = SQLAlchemy()


class User(db.Model):
    """ Basic user data (Used for login or password recovery) """
    uid = Column(String, primary_key=True)
    name = Column(String(64), unique=True)
    email = Column(String(128), unique=True)
    # In case we migrate to a different cipher for passwords
    # 1 = bcrypt
    crypto = Column(Integer)
    password = Column(String)
    # Account status
    # 0 = OK; 1 = banned; 2 = shadowbanned?; 3 = sent to oblivion?
    status = Column(Integer)
    joindate = Column(DateTime)
    posts = db.relationship('SubPost', backref='user', lazy='dynamic')
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
        self.password = bcrypt.hashpw(password.encode(), bcrypt.gensalt())

    def __repr__(self):
        return '<User %r>' % self.name


class UserMetadata(db.Model):
    """ User metadata. Here we store badges, admin status, etc. """
    xid = Column(Integer, primary_key=True)
    uid = Column(Integer, db.ForeignKey('user.uid'))  # Subverse id
    key = Column(String)  # Metadata key
    value = Column(String)


class Sub(db.Model):
    """ Basic sub data """
    sid = Column(String, primary_key=True)  # sub id
    name = Column(String(32), unique=True)  # sub name
    title = Column(String(128))  # sub title/desc

    status = Column(Integer)  # Sub status. 0 = ok; 1 = banned; etc

    posts = db.relationship('SubPost', backref='sub', lazy='dynamic')
    properties = db.relationship('SubMetadata', backref='sub', lazy='dynamic')

    def __init__(self, name, title):
        self.sid = str(uuid.uuid4())
        self.name = name
        self.title = title

    def __repr__(self):
        return '<Sub {0}-{1}>'.format(self.name, self.title)


class SubMetadata(db.Model):
    """ Sub metadata. Here we store if the sub is nsfw, the modlist,
    the founder, etc. """
    xid = Column(Integer, primary_key=True)
    sid = Column(Integer, db.ForeignKey('sub.sid'))  # Subverse id
    key = Column(String)  # Metadata key
    value = Column(String)


class SubPost(db.Model):
    """ Represents a post on a sub """
    pid = Column(Integer, primary_key=True)  # post id
    sid = Column(Integer, db.ForeignKey('sub.sid'))
    uid = Column(Integer, db.ForeignKey('user.uid'))

    # There's a 'sub' field with a reference to the sub and a 'user' one
    # with a refernece to the user that created this post

    title = Column(String(128))  # post title
    link = Column(String(128))  # post target (if it is a link post)
    content = Column(Text)  # post content (if it is a text post)

    posted = Column(DateTime)

    ptype = Column(Integer)  # Post type. 0=normal; 1=mod; etc

    properties = db.relationship('SubPostMetadata',
                                 backref='post', lazy='dynamic')

    comments = db.relationship('SubPostComment', backref='post',
                               lazy='dynamic')

    def __repr__(self):
        return '<SubPost {0} (In Sub{1})>'.format(self.title, self.sid)


class SubPostMetadata(db.Model):
    """ Post metadata. Here we store if it is a sticky post, mod post, tagged
    as nsfw, etc. """
    xid = Column(Integer, primary_key=True)
    pid = Column(Integer, db.ForeignKey('sub_post.pid'))
    key = Column(String)  # Metadata key
    value = Column(String)


class SubPostComment(db.Model):
    """ A comment. In a post. """
    cid = Column(String, primary_key=True)
    pid = Column(Integer, db.ForeignKey('sub_post.pid'))
    uid = Column(Integer, db.ForeignKey('user.uid'))
    time = Column(DateTime)
    content = Column(Text)
    # parent comment id
    parentcid = Column(Integer, db.ForeignKey('sub_post_comment.cid'),
                       nullable=True)
    children = db.relationship("SubPostComment",
                               backref=db.backref("parent", remote_side=cid))

    def __init__(self):
        self.cid = str(uuid.uuid4())


class Message(db.Model):
    """ Represents a post on a sub """
    mid = Column(Integer, primary_key=True)  # msg id
    sentby = Column(Integer, db.ForeignKey('user.uid'))
    receivedby = Column(Integer, db.ForeignKey('user.uid'))

    subject = Column(String(128))  # msg subject
    content = Column(Text)  # msg content

    posted = Column(DateTime)  # sent
    read = Column(DateTime)  # todo markasread time

    mtype = Column(Integer)  # msg type. 0=pm; 1=mod; 2=username mention; etc

    def __repr__(self):
        return '<Messages {0}>'.format(self.subject)
