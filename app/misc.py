""" Misc helper function and classes. """
from urllib.parse import urlparse, parse_qs
import datetime
import time
from sqlalchemy import cast, or_
import requests
import sqlalchemy.orm
import markdown
import sendgrid
import config
from flask_login import AnonymousUserMixin  # , current_user
from .sorting import VoteSorting
from .models import db, Message, SubSubscriber, UserMetadata, SiteMetadata, Sub
from .models import SubPost, SubMetadata, SubPostVote, User, SubPostMetadata
from .models import SubPostCommentVote, SubPostComment
from .caching import cache


class SiteUser(object):
    """ Representation of a site user. Used on the login manager. """

    def __init__(self, userclass=None):
        self.user = userclass
        self.name = self.user.name
        self.is_active = True  # Apply bans by setting this to false.
        if self.user:
            self.is_authenticated = True
            self.is_anonymous = False
            self.admin = getMetadata(self.user, 'admin')
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
        return self.admin

    def is_topmod(self, sub):
        """ Returns True if the current user is a mod of 'sub' """
        return isTopMod(sub, self.user)

    def is_lizard(self):
        """ Returns True if we know that the current user is a lizard. """
        return True if getMetadata(self.user, 'lizard') else False

    def has_mail(self):
        """ Returns True if the current user has unread messages """
        return hasMail(self.user)

    def new_pm_count(self):
        """ Returns new message count """
        return newPMCount(self.user)

    def new_modmail_count(self):
        """ Returns new modmail msg count """
        return newModmailCount(self.user)

    def new_postreply_count(self):
        """ Returns new post reply count """
        return newPostReplyCount(self.user)

    def new_comreply_count(self):
        """ Returns new comment reply count """
        return newComReplyCount(self.user)

    def has_subscribed(self, sub):
        """ Returns True if the current user has subscribed to sub """
        return hasSubscribed(sub, self.user)

    def has_blocked(self, sub):
        """ Returns True if the current user has blocked sub """
        return hasBlocked(sub, self.user)

    def new_count(self):
        """ Returns new message count """
        return newCount(self.user)

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
        posts = SubPost.query.filter_by(uid=self.user.uid)
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
        votes = SubPostVote.query.filter_by(uid=self.user.uid)
        count = 0
        for vote in votes:
            if vote.positive:
                count += 1
            else:
                count -= 1
        return count


class SiteAnon(AnonymousUserMixin):
    """ A subclass of AnonymousUserMixin. Used for logged out users. """

    def get_id(self):
        return False

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


def safeRequest(url):
    """ Gets stuff for the internet, with timeouts and size restrictions """
    # Returns (Response, File)
    max_size = 25000000  # won't download more than 25MB
    recieve_timeout = 10  # won't download for more than 10s
    r = requests.get(url, stream=True, timeout=1)
    r.raise_for_status()

    if int(r.headers.get('Content-Length', 1)) > max_size:
        raise ValueError('response too large')

    size = 0
    start = time.time()
    f = b''
    for chunk in r.iter_content(1024):
        if time.time() - start > recieve_timeout:
            raise ValueError('timeout reached')

        size += len(chunk)
        f += chunk
        if size > max_size:
            raise ValueError('response too large')
    return (r, f)


class URLifyPattern(markdown.inlinepatterns.LinkPattern):
    """ Return a link element from the given match. """
    def handleMatch(self, m):
        el = markdown.util.etree.Element("a")
        el.text = markdown.util.AtomicString(m.group(2))
        href = m.group(2)

        if not href.split('://')[0] in ('http', 'https'):
            if '@' in href and '/' not in href:
                href = 'mailto:' + href
            else:
                href = 'http://' + href
        el.set('href', href)

        return el


class NiceLinkPattern(markdown.inlinepatterns.LinkPattern):
    """ Return a link element from the given match. """
    def handleMatch(self, m):
        el = markdown.util.etree.Element("a")
        el.text = markdown.util.AtomicString(m.group(2))
        if el.text.startswith('@') or el.text.startswith('/u/'):
            href = '/u/' + m.group(4)
        elif el.text.startswith('/s/'):
            href = '/s/' + m.group(4)

        if href:
            if href[0] == "<":
                href = href[1:-1]
            el.set("href", self.sanitize_url(self.unescape(href.strip())))
        else:
            el.set("href", "")

        return el

RE_AMENTION = r'(?<=^|(?<=[^a-zA-Z0-9-_\.]))((@|\/u\/|\/s\/)' \
              '([A-Za-z]+[A-Za-z0-9]+))'


class RestrictedMarkdown(markdown.Extension):
    """ Class to restrict some markdown stuff """
    RE_URL = r'(<(?:f|ht)tps?://[^>]*>|\b(?:f|ht)tps?://[^)<>\s\'"]+[^.,)' \
             r'<>\s\'"]|\bwww\.[^)<>\s\'"]+[^.,)<>\s\'"]|[^(<\s\'"]+\.' \
             r'(?:com|net|org)\b)'

    def extendMarkdown(self, md, md_globals):
        """ Here we disable stuff """
        del md.inlinePatterns['image_link']
        del md.inlinePatterns['image_reference']
        user_tag = NiceLinkPattern(RE_AMENTION, md)
        url = URLifyPattern(self.RE_URL, md)
        md.inlinePatterns.add('user', user_tag, '>strong')
        md.inlinePatterns.add('url', url, '>strong')


@cache.memoize(50)
def hasVoted(uid, post, up=True):
    """ Checks if the user up/downvoted the post. """
    if not uid:
        return False
    vote = SubPostVote.query.filter_by(uid=uid, pid=post.pid).first()
    if vote:
        if vote.positive == up:
            return True
    else:
        return False


@cache.memoize(50)
def hasVotedComment(uid, comment, up=True):
    """ Checks if the user up/downvoted a comment. """
    if not uid:
        return False
    vote = SubPostCommentVote.query.filter_by(uid=uid, cid=comment.cid).first()
    if vote:
        if vote.positive == up:
            return True
    else:
        return False


@cache.memoize(60)
def getCommentParentUID(cid):
    """ Returns the uid of a parent comment """
    parent = SubPostComment.query.filter_by(cid=cid).first()
    return parent.uid


def getComment(cid):
    return SubPostComment.query.get(cid)


def getCommentSub(cid):
    l = getComment(cid)
    p = SubPost.query.get(l.pid)
    return Sub.query.get(p.sid)


@cache.memoize(60)
def getAnnouncement():
    """ Returns sitewide announcement post or False """
    ann = SiteMetadata.query.filter_by(key='announcement').first()
    if ann:
        ann = SubPost.query.filter_by(pid=ann.value).first()
        # This line is here to initialize .user >_>
        # Testing again
    return ann


@cache.memoize(30)
def getMetadata(obj, key, value=None, all=False, record=False, cache=True):
    """ Gets metadata out of 'obj' (either a Sub, SubPost or User) """
    if not obj:
        # Failsafe in case FOR SOME REASON SOMEBODY PASSED NONE OR FALSE TO
        # THIS FUNCTION. IF THIS ACTUALLY HAPPENS YOU SHOULD FEEL BAD FOR
        # PASSING UNVERIFIED DATA.
        return
    if record:
        cache = False
    try:
        x = obj.properties.filter_by(key=key)
    except sqlalchemy.orm.exc.DetachedInstanceError:
        if isinstance(obj, SubPost):
            x = SubPostMetadata.query.filter_by(key=key, pid=obj.pid)
        elif isinstance(obj, Sub):
            x = SubMetadata.query.filter_by(key=key, sid=obj.sid)
        elif isinstance(obj, User):
            x = UserMetadata.query.filter_by(key=key, uid=obj.uid)

    if all:
        x = x.all()
    else:
        x = x.first()

    if x and value is None:
        if all or record:
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
    x = SubMetadata.query.filter_by(key='mod1', sid=sub.sid, value=user.uid)
    if x.first():
        return True

    y = SubMetadata.query.filter_by(key='mod2', sid=sub.sid, value=user.uid)
    if y.first():
        return True
    return False


def isSubBan(sub, user):
    """ Returns True if 'user' is banned 'sub' """
    x = SubMetadata.query.filter_by(key='ban', sid=sub.sid, value=user.uid)
    return bool(x.first())


def isTopMod(sub, user):
    """ Returns True if 'user' is a topmod of 'sub' """
    x = SubMetadata.query.filter_by(key='mod1', sid=sub.sid, value=user.uid)
    return bool(x.first())


def isModInv(sub, user):
    """ Returns True if 'user' is a invited to mod of 'sub' """
    x = SubMetadata.query.filter_by(key='mod2i', sid=sub.sid, value=user.uid)
    return bool(x.first())


def hasMail(user):
    """ Returns True if the current user has unread messages """
    x = Message.query.filter_by(receivedby=user.uid) \
                     .filter(Message.mtype != 6) \
                     .filter_by(read=None).first()
    return bool(x)


def newPMCount(user):
    """ Returns new message count in message area"""
    x = Message.query.filter_by(read=None).filter(or_(Message.mtype == 1,
                                                      Message.mtype == 8)) \
                     .filter_by(receivedby=user.uid).count()
    return x


def newModmailCount(user):
    """ Returns new replies count in message area """
    x = Message.query.filter_by(read=None) \
                     .filter(or_(Message.mtype == 2, Message.mtype == 7)) \
                     .filter_by(receivedby=user.uid).count()
    return x


def newPostReplyCount(user):
    """ Returns new replies count in message area """
    x = Message.query.filter_by(read=None).filter_by(mtype=4) \
                     .filter_by(receivedby=user.uid).count()
    return x


def newComReplyCount(user):
    """ Returns new comment replies count in message area """
    x = Message.query.filter_by(read=None).filter_by(mtype=5) \
                     .filter_by(receivedby=user.uid).count()
    return x


def hasSubscribed(sub, user):
    """ Returns True if the current user is subscribed """
    x = SubSubscriber.query.filter_by(sid=sub.sid, uid=user.uid, status=1)
    return bool(x.first())


def hasBlocked(sub, user):
    """ Returns True if the current user has blocked """
    x = SubSubscriber.query.filter_by(sid=sub.sid, uid=user.uid, status=2)
    return bool(x.first())


@cache.memoize(600)
def getSubUsers(sub, key):
    """ Returns the names of the sub positions, founder, owner """
    x = SubMetadata.query.filter_by(sid=sub.sid, key=key).first()

    name = User.query.get(x.value).name
    return name


@cache.memoize(600)
def getSubCreation(sub):
    """ Returns the sub's 'creation' metadata """
    x = getMetadata(sub, 'creation')
    return x.replace(' ', 'T')  # Converts to ISO format


@cache.memoize(60)
def getSuscriberCount(sub):
    """ Returns subscriber count """
    x = SubSubscriber.query.filter_by(sid=sub.sid, status=1)
    try:
        return len(list(x))
    except StopIteration:
        return 0


@cache.memoize(60)
def getModCount(sub):
    """ Returns the sub's mod count metadata """
    x = getMetadata(sub, 'mod2', all=True)

    return len(x)


@cache.memoize(60)
def getSubPostCount(sub):
    """ Returns the sub's post count """
    y = SubPost.query.filter_by(sid=sub.sid).count()
    return y


def getStickies(sid):
    """ Returns a list of stickied SubPosts """
    x = SubMetadata.query.filter_by(sid=sid, key='sticky')
    try:
        x = list(x)
    except StopIteration:
        x = []
    r = []
    for i in x:
        r.append(SubPost.query.get(i.value))
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


def enableVideoMode(sub):
    """ Returns true if the sub has video/music player enabled """
    x = getMetadata(sub, 'videomode')
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


@cache.memoize(600)
def getDefaultSubs():
    """ Returns a list of all the default subs """
    md = list(SiteMetadata.query.filter_by(key='default'))
    defaults = []
    for sub in md:
        sub = Sub.query.get(sub.value)
        defaults.append(sub)
    return defaults


def getSubscriptions(uid):
    """ Returns all the subs the current user is subscribed to """
    if uid:
        subs = SubSubscriber.query.filter_by(uid=uid,
                                             status=1)
    else:
        subs = getDefaultSubs()
    return list(subs)


@cache.memoize(600)
def enableBTCmod():
    """ Returns true if BTC donation module is enabled """
    x = SiteMetadata.query.filter_by(key='usebtc').first()
    return False if not x or x.value == '0' else True


@cache.memoize(600)
def getBTCmsg():
    """ Returns donation module text """
    x = SiteMetadata.query.filter_by(key='btcmsg').first()
    if x:
        return x.value


@cache.memoize(600)
def getBTCaddr():
    """ Returns Bitcoin address """
    x = SiteMetadata.query.filter_by(key='btcaddr').first()
    if x:
        return x.value


def getTodaysTopPosts():
    """ Returns top posts in the last 24 hours """
    since = datetime.datetime.utcnow() - datetime.timedelta(hours=24)
    posts = SubPost.query.filter(SubPost.posted > since).all()
    posts = VoteSorting(posts).getPosts(1)
    return list(posts)[:5]


def sendMail(to, subject, content):
    """ Sends a mail through sendgrid """
    sg = sendgrid.SendGridAPIClient(api_key=config.SENDGRID_API_KEY)

    from_email = sendgrid.Email(config.SENDGRID_DEFAULT_FROM)
    to_email = sendgrid.Email(to)
    content = sendgrid.helpers.mail.Content('text/html', content)

    mail = sendgrid.helpers.mail.Mail(from_email, subject, to_email,
                                      content)

    sg.client.mail.send.post(request_body=mail.get())


def getYoutubeID(url):
    """ Returns youtube ID for a video. """
    url = urlparse(url)
    if url.hostname == 'youtu.be':
        return url.path[1:]
    if url.hostname in ['www.youtube.com', 'youtube.com']:
        if url.path == '/watch':
            p = parse_qs(url.query)
            return p['v'][0]
        if url.path[:3] == '/v/':
            return url.path.split('/')[2]
    # fail?
    return None


def moddedSubCount(user):
    """ Returns the number of subs a user is modding """
    sub1 = SubMetadata.query.filter_by(key='mod1', value=user).count()
    sub2 = SubMetadata.query.filter_by(key='mod2', value=user).count()
    return sub1 + sub2


def newCount(user):
    """ Returns new message count """
    x = Message.query.filter(Message.read.is_(None),
                             Message.receivedby == user.uid) \
                     .filter(Message.mtype != 6)
    return len(list(x))


@cache.memoize(30)
def getPostsFromSubs(subs):
    posts = []
    for sub in subs:
        posts.append(SubPost.sid == sub.sid)
    posts = SubPost.query.filter(or_(*posts)).all()
    return posts
