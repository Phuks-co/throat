""" Misc helper function and classes. """
from sqlalchemy import or_

from .models import db, Message, SubSubscriber, UserMetadata, SiteMetadata
from .models import SubPost, SubMetadata, SubPostVote, User
from flask_login import AnonymousUserMixin
from flask_cache import Cache

cache = Cache()


class SiteUser(object):
    """ Representation of a site user. Used on the login manager. """

    def __init__(self, userclass=None):
        self.user = userclass
        self.is_active = True  # Apply bans by setting this to false.
        if self.user:
            self.is_authenticated = True
            self.is_anonymous = False
        else:
            self.is_authenticated = False
            self.is_anonymous = True

    def get_id(self):
        """ Returns the unique user id. Used on load_user """
        return str(self.user.uid)

    def get_username(self):
        """ Returns the unique user name. Used on load_user """
        return self.user.name

    def is_mod(self, sub):
        """ Returns True if the current user is a mod of 'sub' """
        return isMod(sub, self.user)

    def is_subban(self, sub):
        """ Returns True if the current user is banned from 'sub' """
        return isSubBan(sub, self.user)

    def is_modinv(self, sub):
        """ Returns True if the current user is invited to mod of 'sub' """
        return isModInv(sub, self.user)

    def is_admin(self):
        """ Returns true if the current user is a site admin. """
        return True if getMetadata(self.user, 'admin') else False

    def is_topmod(self, sub):
        """ Returns True if the current user is a mod of 'sub' """
        return isTopMod(sub, self.user)

    def is_lizard(self):
        """ Returns True if we know that the current user is a lizard. """
        return True if getMetadata(self.user, 'lizard') else False

    def has_mail(self):
        """ Returns True if the current user has unread messages """
        return hasMail(self.user)

    def new_count(self):
        """ Returns new message count """
        return newCount(self.user)

    def has_subscribed(self, sub):
        """ Returns True if the current user has subscribed to sub """
        return hasSubscribed(sub, self.user)

    def has_blocked(self, sub):
        """ Returns True if the current user has blocked sub """
        return hasBlocked(sub, self.user)

    def has_exlinks(self):
        """ Returns true if user selects to open links in a new window """
        x = UserMetadata.query.filter_by(uid=self.user.uid) \
                              .filter_by(key='exlinks').first()
        if x:
            return True if x.value == '1' else False
        else:
            return False

    def block_styles(self):
        """ Returns true if user selects to block sub styles """
        x = UserMetadata.query.filter_by(uid=self.user.uid) \
                              .filter_by(key='styles').first()
        if x:
            return True if x.value == '1' else False
        else:
            return False

    def show_nsfw(self):
        """ Returns true if user selects show nsfw posts """
        x = UserMetadata.query.filter_by(uid=self.user.uid) \
                              .filter_by(key='nsfw').first()
        if x:
            return True if x.value == '1' else False
        else:
            return False


class SiteAnon(AnonymousUserMixin):
    """ A subclass of AnonymousUserMixin. Used for logged out users. """
    @classmethod
    def is_mod(cls, sub):
        """ Anons are not mods. """
        return False

    @classmethod
    def is_admin(cls):
        """ Anons are not admins. """
        return False

    @classmethod
    def is_topmod(cls, sub):
        """ Anons are not owners. """
        return False

    @classmethod
    def is_lizard(cls):
        """ We don't know if anons are lizards...
            We return False just in case """
        return False  # We don't know :(

    @classmethod
    def has_subscribed(cls, sub):
        """ Anons dont get subscribe options. """
        return False

    @classmethod
    def has_blocked(cls, sub):
        """ Anons dont get blocked options. """
        return False

    @classmethod
    def has_exlinks(cls):
        """ Anons dont get usermetadata options. """
        return False

    @classmethod
    def block_styles(cls):
        """ Anons dont get usermetadata options. """
        return False

    @classmethod
    def show_nsfw(cls):
        """ Anons dont get usermetadata options. """
        return False

    @classmethod
    def is_modinv(cls):
        """ Anons dont get see submod page. """
        return False

    def is_subban(cls, sub):
        """ Anons dont get banned by default. """
        return False


def getVoteCount(post):
    """ Returns the vote count of a post. The parameter is the
    SubPost object """
    count = 0
    for vote in post.votes:
        if vote.positive:
            count += 1
        else:
            count -= 1

    return count


@cache.memoize(50)
def hasVoted(uid, post, up=True):
    """ Checks if the user up/downvoted the post. """
    vote = SubPostVote.query.filter_by(uid=uid, pid=post.pid).first()
    if vote:
        if vote.positive == up:
            return True
    else:
        return False


@cache.memoize(60)
def getAnnouncement():
    """ Returns sitewide announcement post or False """
    ann = SiteMetadata.query.filter_by(key='announcement').first()
    if ann:
        ann = SubPost.query.filter_by(pid=ann.value).first()
        # This line is here to initialize .user >_>
        test = ann.user.name
    return ann


@cache.memoize(60)
def getMetadata(obj, key, value=None):
    """ Gets metadata out of 'obj' (either a Sub, SubPost or User) """
    if not obj:
        # Failsafe in case FOR SOME REASON SOMEBODY PASSED NONE OR FALSE TO
        # THIS FUNCTION. IF THIS ACTUALLY HAPPENS YOU SHOULD FEEL BAD FOR
        # PASSING UNVERIFIED DATA.
        return
    x = obj.properties.filter_by(key=key).first()
    if x and value is None:
        return x.value
    elif value is None:
        return False
    if x:
        x.value = value
    else:
        x = obj.__class__(obj, key, value)
        db.session.add(x)
    db.session.commit()


def isMod(sub, user):
    """ Returns True if 'user' is a mod of 'sub' """
    x = sub.properties.filter_by(key='mod1').filter_by(value=user.uid).first()
    y = sub.properties.filter_by(key='mod2').filter_by(value=user.uid).first()
    if x or y:
        return True
    else:
        return False

def isSubBan(sub, user):
    """ Returns True if 'user' is banned 'sub' """
    x = sub.properties.filter_by(key='ban').filter_by(value=user.uid).first()
    return bool(x)

def isTopMod(sub, user):
    """ Returns True if 'user' is a topmod of 'sub' """
    x = sub.properties.filter_by(key='mod1').filter_by(value=user.uid).first()
    return bool(x)


def isModInv(sub, user):
    """ Returns True if 'user' is a invited to mod of 'sub' """
    x = sub.properties.filter_by(key='mod2i').filter_by(value=user.uid).first()
    return bool(x)


def hasMail(user):
    """ Returns True if the current user has unread messages """
    x = Message.query.filter_by(receivedby=user.uid) \
                     .filter(or_(Message.mtype.is_(None)) | \
                     (Message.mtype != '-1')) \
                     .filter_by(read=None).first()
    return bool(x)


def newCount(user):
    """ Returns new message count """
    newcount = Message.query.filter_by(read=None) \
                            .filter(or_(Message.mtype.is_(None)) | \
                            (Message.mtype != '-1')) \
                            .filter_by(receivedby=user.uid).count()
    return newcount


def hasSubscribed(sub, user):
    """ Returns True if the current user is subscribed """
    x = SubSubscriber.query.filter_by(sid=sub.sid) \
                           .filter_by(uid=user.uid) \
                           .filter_by(status='1').first()
    return bool(x)


def hasBlocked(sub, user):
    """ Returns True if the current user has blocked """
    x = SubSubscriber.query.filter_by(sid=sub.sid) \
                           .filter_by(uid=user.uid) \
                           .filter_by(status='2').first()
    return bool(x)


@cache.memoize(600)
def getSubUsers(sub, key):
    """ Returns the names of the sub positions, founder, owner """
    x = SubMetadata.query.filter_by(sid=sub.sid) \
                         .filter_by(key=key).first()
    y = User.query.filter_by(uid=x.value).first()
    return y.name


@cache.memoize(600)
def getSubCreation(sub):
    """ Returns the sub's 'creation' metadata """
    x = sub.properties.filter_by(key='creation').first()
    return x.value


@cache.memoize(300)
def getSuscriberCount(sub):
    """ Returns subscriber count """
    x = sub.subscribers.filter_by(sid=sub.sid) \
                        .filter_by(status='1').count()
    return x
