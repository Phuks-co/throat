""" Misc helper function and classes. """
from sqlalchemy import or_
import markdown
from flask_login import AnonymousUserMixin, current_user
from flask_cache import Cache
import sqlalchemy.orm
from .models import db, Message, SubSubscriber, UserMetadata, SiteMetadata, Sub
from .models import SubPost, SubMetadata, SubPostVote, User, SubPostMetadata

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

    def new_pm_count(self):
        """ Returns new message count """
        return newPMCount(self.user)

    def new_reply_count(self):
        """ Returns new message count """
        return newReplyCount(self.user)

    def has_subscribed(self, sub):
        """ Returns True if the current user has subscribed to sub """
        return hasSubscribed(sub, self.user)

    def has_blocked(self, sub):
        """ Returns True if the current user has blocked sub """
        return hasBlocked(sub, self.user)

    @cache.memoize(60)
    def has_exlinks(self):
        """ Returns true if user selects to open links in a new window """
        x = getMetadata(self.user, 'exlinks')
        if x:
            return True if x == '1' else False
        else:
            return False

    @cache.memoize(60)
    def block_styles(self):
        """ Returns true if user selects to block sub styles """
        x = getMetadata(self.user, 'styles')
        if x:
            return True if x == '1' else False
        else:
            return False

    @cache.memoize(60)
    def show_nsfw(self):
        """ Returns true if user selects show nsfw posts """
        x = getMetadata(self.user, 'nsfw')
        if x:
            return True if x == '1' else False
        else:
            return False

    @cache.memoize(60)
    def get_post_score(self):
        """ Returns the post vote score of a user. """
        posts = SubPost.cache.filter(uid=self.user.uid)
        count = 0
        for post in posts:
            for vote in post.votes:
                if vote.positive:
                    count += 1
                else:
                    count -= 1
        return count

    @cache.memoize(60)
    def get_post_voting(self):
        """ Returns the post voting for a user. """
        votes = SubPostVote.cache.filter(uid=self.user.uid)
        count = 0
        for vote in votes:
            if vote.positive:
                count += 1
            else:
                count -= 1
        return count


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

    @classmethod
    def is_subban(cls, sub):
        """ Anons dont get banned by default. """
        return False


class RestrictedMarkdown(markdown.Extension):
    """ Class to restrict some markdown stuff """
    def extendMarkdown(self, md, md_globals):
        """ Here we disable stuff """
        del md.inlinePatterns['image_link']
        del md.inlinePatterns['image_reference']


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
        # Testing again
        test = [ann.user.name, ann.sub.name]
    return ann


def decent(q):
    """ Makes querying shit easier """
    try:
        return next(q)
    except StopIteration:
        return None


@cache.memoize(30)
def getMetadata(obj, key, value=None, all=False, record=False):
    """ Gets metadata out of 'obj' (either a Sub, SubPost or User) """
    if not obj:
        # Failsafe in case FOR SOME REASON SOMEBODY PASSED NONE OR FALSE TO
        # THIS FUNCTION. IF THIS ACTUALLY HAPPENS YOU SHOULD FEEL BAD FOR
        # PASSING UNVERIFIED DATA.
        return

    try:
        if all:
            x = obj.properties.filter_by(key=key).all()
        else:
            x = obj.properties.filter_by(key=key).first()
    except (AttributeError, sqlalchemy.orm.exc.DetachedInstanceError):
        if isinstance(obj, SubPost):
            x = SubPostMetadata.cache.filter(key=key, pid=obj.pid)
        elif isinstance(obj, Sub):
            x = SubMetadata.cache.filter(key=key, sid=obj.sid)
        elif isinstance(obj, User):
            x = UserMetadata.cache.filter(key=key, uid=obj.uid)
        try:
            if all:
                x = list(x)
            else:
                x = next(x)
        except StopIteration:
            return False
    if x and value is None:
        if all:
            return x
        if record:
            return x
        return x.value
    elif value is None:
        if all:
            return []
        return False
    if x:
        x.value = value
    else:
        x = obj.__class__(obj, key, value)
        db.session.add(x)
    db.session.commit()


def isMod(sub, user):
    """ Returns True if 'user' is a mod of 'sub' """
    x = SubMetadata.cache.filter(key='mod1', sid=sub.sid, value=user.uid)
    try:
        x = next(x)
    except StopIteration:
        x = False

    y = SubMetadata.cache.filter(key='mod2', sid=sub.sid, value=user.uid)
    try:
        y = next(y)
    except StopIteration:
        y = False
    return bool(x or y)


def isSubBan(sub, user):
    """ Returns True if 'user' is banned 'sub' """
    x = SubMetadata.cache.filter(key='ban', sid=sub.sid, value=user.uid)
    try:
        x = next(x)
    except StopIteration:
        x = False
    return bool(x)


def isTopMod(sub, user):
    """ Returns True if 'user' is a topmod of 'sub' """
    x = SubMetadata.cache.filter(key='mod1', sid=sub.sid, value=user.uid)
    try:
        x = next(x)
    except StopIteration:
        x = False
    return bool(x)


def isModInv(sub, user):
    """ Returns True if 'user' is a invited to mod of 'sub' """
    x = SubMetadata.cache.filter(key='mod2i', sid=sub.sid, value=user.uid)
    try:
        x = next(x)
    except StopIteration:
        x = False
    return bool(x)


def hasMail(user):
    """ Returns True if the current user has unread messages """
    x = Message.query.filter_by(receivedby=user.uid) \
                     .filter(or_(Message.mtype.is_(None)) |
                             (Message.mtype != '-1')) \
                     .filter_by(read=None).first()
    return bool(x)


def newCount(user):
    """ Returns new message count """
    x = Message.cache.filter(read=None, receivedby=user.uid)
    return len(list(x))


def newPMCount(user):
    """ Returns new message count in message area"""
    x = Message.query.filter_by(read=None).filter(Message.mtype=='0') \
                     .filter_by(receivedby=user.uid).count()
    return x


def newReplyCount(user):
    """ Returns new message count in message area """
    x = Message.query.filter_by(read=None).filter(Message.mtype!=None) \
                     .filter_by(receivedby=user.uid).count()
    return x


def hasSubscribed(sub, user):
    """ Returns True if the current user is subscribed """
    x = SubSubscriber.cache.filter(sid=sub.sid, uid=user.uid, status='1')
    try:
        x = next(x)
    except StopIteration:
        x = False
    return bool(x)


def hasBlocked(sub, user):
    """ Returns True if the current user has blocked """
    x = SubSubscriber.cache.filter(sid=sub.sid, uid=user.uid, status='2')
    try:
        x = next(x)
    except StopIteration:
        x = False
    return bool(x)


@cache.memoize(600)
def getSubUsers(sub, key):
    """ Returns the names of the sub positions, founder, owner """
    x = SubMetadata.cache.filter(sid=sub.sid, key=key)
    try:
        x = next(x)
    except StopIteration:
        return False

    name = User.cache.get(x.value).name
    return name


@cache.memoize(600)
def getSubCreation(sub):
    """ Returns the sub's 'creation' metadata """
    x = getMetadata(sub, 'creation')
    return x


@cache.memoize(300)
def getSuscriberCount(sub):
    """ Returns subscriber count """
    x = SubSubscriber.cache.filter(sid=sub.sid, status=1)
    try:
        return len(list(x))
    except StopIteration:
        return 0


@cache.memoize(300)
def getModCount(sub):
    """ Returns the sub's mod count metadata """
    x = getMetadata(sub, 'mod2', all=True)

    return len(x)


@cache.memoize(300)
def getSubPostCount(sub):
    """ Returns the sub's post count """
    x = Sub.query.filter_by(name=sub.name).first()
    y = SubPost.query.filter_by(sid=sub.sid).count()
    #x = SubPost.cache.filter(sid=sub.sid)
    #try:
    #    x = list(x)
    #except StopIteration:
    #    x = 0
    return y


def getStickies(sid):
    """ Returns a list of stickied SubPosts """
    x = SubMetadata.cache.filter(sid=sid, key='sticky')
    try:
        x = list(x)
    except StopIteration:
        x = []
    r = []
    for i in x:
        r.append(SubPost.cache.get(i.value))
    return r


def isRestricted(sub):
    """ Returns true if the sub is marked as Restricted """
    x = getMetadata(sub, 'restricted')
    return False if not x or x == '0' else True


def isNSFW(sub):
    """ Returns true if the sub is marked as NSFW """
    x = getMetadata(sub, 'nsfw')
    return False if not x or x == '0' else True


def userCanFlair(sub):
    """ Returns true if the sub allows users to pick their own flair """
    x = getMetadata(sub, 'ucf')
    return False if not x or x == '0' else True


def subSort(sub):
    """ Don't forget to add the fucking docstring to functions >:| """
    # What an useful docstring.
    x = getMetadata(sub, 'sort')
    if not x or x == 'v':
        return 'Hot'
    if x == 'v_two':
        return 'New'
    if x == 'v_three':
        return 'Top'


def hasPostFlair(post):
    """ Returns true if the post has assigned flair """
    x = getMetadata(post, 'flair')
    return x


def getPostFlair(post, fl):
    """ Returns true if the post has available flair """
    return getMetadata(post, fl)


def getSubscriptions():
    subs = SubSubscriber.cache.filter(uid=current_user.user.uid, status='1')
    return list(subs)
