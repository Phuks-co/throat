""" Misc helper function and classes. """
from urllib.parse import urlparse, parse_qs
import time
import re
# from sqlalchemy import or_, func
import requests
import markdown
import sendgrid
import config
from flask import url_for
from flask_login import AnonymousUserMixin, current_user
from .sorting import VoteSorting
# from .models import db, Message, SubSubscriber, UserMetadata, Sub
# from .models import SubPost, SubMetadata, SubPostVote, User, SubPostMetadata
# from .models import SubPostCommentVote, SubPostComment
from .caching import cache
from . import database as db


class SiteUser(object):
    """ Representation of a site user. Used on the login manager. """

    def __init__(self, userclass=None):
        self.user = userclass
        self.name = self.user['name']
        self.uid = self.user['uid']
        self.is_active = True  # Apply bans by setting this to false.
        if self.user:
            self.is_authenticated = True
            self.is_anonymous = False
            self.admin = bool(db.get_user_metadata(self.uid, 'admin'))
        else:
            self.is_authenticated = False
            self.is_anonymous = True

    def get_id(self):
        """ Returns the unique user id. Used on load_user """
        return self.uid

    def get_username(self):
        """ Returns the user name. Used on load_user """
        return self.name

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

    def has_mail(self):
        """ Returns True if the current user has unread messages """
        return bool(db.user_mail_count(self.uid))

    def new_pm_count(self):
        """ Returns new message count """
        x = db.query('SELECT COUNT(*) AS c FROM `message` WHERE `read` IS NULL'
                     ' AND `mtype` IN (1, 8) AND `receivedby`=%s',
                     (self.user['uid'],)).fetchone()['c']
        return x

    def new_modmail_count(self):
        """ Returns new modmail msg count """
        x = db.query('SELECT COUNT(*) AS c FROM `message` WHERE `read` IS NULL'
                     ' AND `mtype` IN (2, 7) AND `receivedby`=%s',
                     (self.user['uid'],)).fetchone()['c']
        return x

    def new_postreply_count(self):
        """ Returns new post reply count """
        x = db.query('SELECT COUNT(*) AS c FROM `message` WHERE `read` IS NULL'
                     ' AND `mtype`=4 AND `receivedby`=%s',
                     (self.user['uid'],)).fetchone()['c']
        return x

    def new_comreply_count(self):
        """ Returns new comment reply count """
        x = db.query('SELECT COUNT(*) AS c FROM `message` WHERE `read` IS NULL'
                     ' AND `mtype`=5 AND `receivedby`=%s',
                     (self.user['uid'],)).fetchone()['c']
        return x

    def has_subscribed(self, sid):
        """ Returns True if the current user has subscribed to sub """
        x = db.query('SELECT xid FROM `sub_subscriber` '
                     'WHERE `sid`=%s AND `uid`=%s AND `status`=%s',
                     (sid, self.uid, 1))
        return bool(x.fetchone())

    def has_blocked(self, sid):
        """ Returns True if the current user has blocked sub """
        x = db.query('SELECT xid FROM `sub_subscriber` '
                     'WHERE `sid`=%s AND `uid`=%s AND `status`=%s',
                     (sid, self.uid, 2))
        return bool(x.fetchone())

    def new_count(self):
        """ Returns new message count """
        return db.user_mail_count(self.uid)

    @cache.memoize(300)
    def has_exlinks(self):
        """ Returns true if user selects to open links in a new window """
        x = db.get_user_metadata(self.uid, 'exlinks')
        if x:
            return True if x == '1' else False
        else:
            return False

    @cache.memoize(300)
    def block_styles(self):
        """ Returns true if user selects to block sub styles """
        x = db.get_user_metadata(self.uid, 'nostyles')
        if x:
            return True if x == '1' else False
        else:
            return False

    @cache.memoize(300)
    def show_nsfw(self):
        """ Returns true if user selects show nsfw posts """
        return db.get_user_metadata(self.uid, 'nsfw')

    @cache.memoize(300)
    def get_post_score(self):
        """ Returns the post vote score of a user. """
        if self.user['score'] is None:
            mposts = db.query('SELECT * FROM `sub_post` WHERE `uid`=%s',
                              (self.uid, )).fetchall()

            q = "SELECT `positive` FROM `sub_post_vote` WHERE `pid` IN ("
            l = []
            for post in mposts:
                q += '%s, '
                l.append(post['pid'])
            q = q[:-2] + ")"
            count = 0

            if l:
                votes = db.query(q, list(l)).fetchall()

                for vote in votes:
                    if vote['positive']:
                        count += 1
                    else:
                        count -= 1

            mposts = db.query('SELECT * FROM `sub_post_comment` WHERE '
                              '`uid`=%s', (self.uid, )).fetchall()
            q = "SELECT `positive` FROM `sub_post_comment_vote`"
            q += " WHERE `cid` IN ("

            l = []
            for post in mposts:
                q += '%s, '
                l.append(post['cid'])
            q = q[:-2] + ")"
            count = 0

            if l:
                votes = db.query(q, list(l)).fetchall()

                for vote in votes:
                    if vote['positive']:
                        count += 1
                    else:
                        count -= 1

            db.uquery('UPDATE `user` SET `score`=%s WHERE `uid`=%s',
                      (count, self.uid))
            return count
        return self.user['score']

    @cache.memoize(120)
    def get_post_voting(self):
        """ Returns the post voting for a user. """
        return db.get_user_post_voting(self.uid)


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
              r'([A-Za-z]+[A-Za-z0-9\-\_]+))'


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
        md.inlinePatterns.add('user', user_tag, '<not_strong')
        md.inlinePatterns.add('url', url, '>user')


def our_markdown(text):
    """ Here we create a custom markdown function where we load all the
    extensions we need. """
    return markdown.markdown(text,
                             extensions=['markdown.extensions.tables',
                                         RestrictedMarkdown()],
                             safe_mode='escape')


@cache.memoize(5)
def getVoteStatus(uid, pid):
    """ Returns if the user voted positively or negatively to a post """
    c = db.query('SELECT positive FROM `sub_post_vote` WHERE `uid`=%s'
                 ' AND `pid`=%s', (uid, pid, ))
    vote = c.fetchone()
    if not vote:
        return -1
    return int(vote['positive'])


@cache.memoize(50)
def hasVotedComment(uid, comment, up=True):
    """ Checks if the user up/downvoted a comment. """
    if not uid:
        return False
    vote = db.query('SELECT `positive` FROM `sub_post_comment_vote` WHERE '
                    '`uid`=%s AND `cid`=%s', (uid, comment['cid'])).fetchone()
    if vote:
        if vote['positive'] == up:
            return True
    else:
        return False


@cache.memoize(600)
def getCommentParentUID(cid):
    """ Returns the uid of a parent comment """
    comm = db.get_comment_from_cid(cid)
    parent = db.get_comment_from_cid(comm['parentcid'])
    return parent['uid']


def getCommentSub(cid):
    """ Returns the sub for a comment """
    l = db.get_comment_from_cid(cid)

    return db.get_sub_from_pid(l['pid'])


@cache.memoize(600)
def getAnnouncement():
    """ Returns sitewide announcement post or False """
    ann = db.get_site_metadata('announcement')
    if ann:
        ann = db.get_post_from_pid(ann['value'])
    return ann


def isMod(sub, user):
    """ Returns True if 'user' is a mod of 'sub' """
    x = db.get_sub_metadata(sub['sid'], 'mod1', value=user['uid'])
    if x:
        return True

    x = db.get_sub_metadata(sub['sid'], 'mod2', value=user['uid'])
    if x:
        return True
    return False


@cache.memoize(30)
def isSubBan(sub, user):
    """ Returns True if 'user' is banned 'sub' """
    x = db.get_sub_metadata(sub['sid'], 'ban', value=user['uid'])
    return x


@cache.memoize(30)
def isTopMod(sub, user):
    """ Returns True if 'user' is a topmod of 'sub' """
    x = db.get_sub_metadata(sub['sid'], 'mod1', value=user['uid'])
    return x


def isModInv(sub, user):
    """ Returns True if 'user' is a invited to mod of 'sub' """
    x = db.get_sub_metadata(sub['sid'], 'mod2i', value=user['uid'])
    return x


@cache.memoize(600)
def getSubUsers(sub, key):
    """ Returns the names of the sub positions, founder, owner """
    x = db.get_sub_metadata(sub['sid'], key)
    if x:
        return db.get_user_from_uid(x['value'])['name']


@cache.memoize(600)
def getSubCreation(sub):
    """ Returns the sub's 'creation' metadata """
    x = db.get_sub_metadata(sub['sid'], 'creation')
    return x['value'].replace(' ', 'T')  # Converts to ISO format


@cache.memoize(60)
def getSuscriberCount(sub):
    """ Returns subscriber count """
    x = db.query('SELECT COUNT(*) AS count FROM `sub_subscriber` '
                 'WHERE `sid`=%s AND `status`=%s', (sub['sid'], 1))
    return x.fetchone()['count']


@cache.memoize(60)
def getModCount(sub):
    """ Returns the sub's mod count metadata """
    x = db.query('SELECT COUNT(*) AS c FROM `sub_metadata` WHERE '
                 '`sid`=%s AND `key`=%s', (sub['sid'], 'mod2')).fetchone()

    return x['c']


@cache.memoize(60)
def getSubPostCount(sub):
    """ Returns the sub's post count """
    y = db.query('SELECT COUNT(*) AS c FROM `sub` WHERE `sid`=%s',
                 (sub['sid'],)).fetchone()['c']
    return y


@cache.memoize(60)
def getStickies(sid):
    """ Returns a list of stickied SubPosts """
    x = db.get_sub_metadata(sid, 'sticky', _all=True)
    r = []
    for i in x:
        r.append(db.get_post_from_pid(i['value']))
    return r


@cache.memoize(60)
def isRestricted(sub):
    """ Returns true if the sub is marked as Restricted """
    x = db.get_sub_metadata(sub['sid'], 'restricted')
    return False if not x or x['value'] == '0' else True


def isNSFW(sub):
    """ Returns true if the sub is marked as NSFW """
    x = sub['nsfw']
    return False if not x or x == '0' else True


def userCanFlair(sub):
    """ Returns true if the sub allows users to pick their own flair """
    x = db.get_sub_metadata(sub['sid'], 'ucf')
    return False if not x or x['value'] == '0' else True


def enableVideoMode(sub):
    """ Returns true if the sub has video/music player enabled """
    x = db.get_sub_metadata(sub['sid'], 'videomode')
    return False if not x or x['value'] == '0' else True


@cache.memoize(5)
def getPostFlair(post):
    """ Returns true if the post has available flair """
    f = db.get_post_metadata(post['pid'], 'flair')
    if not f:
        return False
    else:
        return f['value']


@cache.memoize(600)
def getDefaultSubs():
    """ Returns a list of all the default subs """
    md = db.get_site_metadata('default', True)
    defaults = []
    for sub in md:
        defaults.append({'sid': sub['value']})
    return defaults


def getSubscriptions(uid):
    """ Returns all the subs the current user is subscribed to """
    if uid:
        subs = db.get_user_subscriptions(uid)
    else:
        subs = getDefaultSubs()
    return list(subs)


@cache.memoize(600)
def enableBTCmod():
    """ Returns true if BTC donation module is enabled """
    x = db.get_site_metadata('usebtc')
    return False if not x or x['value'] == '0' else True


@cache.memoize(600)
def getBTCmsg():
    """ Returns donation module text """
    x = db.get_site_metadata('btcmsg')
    if x:
        return x['value']


@cache.memoize(600)
def getBTCaddr():
    """ Returns Bitcoin address """
    x = db.get_site_metadata('btcaddr')
    if x:
        return x['value']


def getTodaysTopPosts():
    """ Returns top posts in the last 24 hours """
    c = db.query('SELECT * FROM `sub_post` WHERE '
                 '`posted` > NOW() - INTERVAL 1 DAY')
    posts = c.fetchall()
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


def moddedSubCount(uid):
    """ Returns the number of subs a user is modding """
    sub = db.query('SELECT COUNT(*) AS c FROM `sub_metadata` WHERE `value`=%s '
                   "AND `key` IN ('mod1', 'mod2')", (uid,))
    return sub.fetchone()['c']


@cache.memoize(120)
def getPostsFromSubs(subs):
    """ Returns all posts from a list or subs """
    if not subs:
        return []
    qbody = "SELECT * FROM `sub_post` WHERE "
    qdata = []
    for sub in subs:
        qbody += "`sid`=%s OR "
        qdata.append(sub['sid'])
    c = db.query(qbody[:-3], tuple(qdata))
    return c.fetchall()


def workWithMentions(data, receivedby, post, sub):
    """ Does all the job for mentions """
    mts = re.findall(RE_AMENTION, data)
    if mts:
        mts = list(set(mts))  # Removes dupes
        # Filter only users
        mts = [x[2] for x in mts if x[1] == "/u/" or x[1] == "@"]
        for mtn in mts[:5]:
            # Send notifications.
            user = db.get_user_from_name(mtn)
            if not user:
                continue
            if user['uid'] != current_user.uid and user['uid'] != receivedby:
                # Checks done. Send our shit
                link = url_for('view_post', pid=post['pid'], sub=sub['name'])
                db.create_message(current_user.uid, user['uid'],
                                  subject="You've been tagged in a post",
                                  content="[{0}]({1}) tagged you in [{2}]({3})"
                                  .format(
                                      current_user.get_username(),
                                      url_for(
                                          'view_user',
                                          user=current_user.name),
                                      "Here: " + post['title'], link),
                                  link=link,
                                  mtype=8)


def getSub(sid):
    """ Returns sub from sid, db proxy now """
    return db.get_sub_from_sid(sid)


def getUser(uid):
    """ Returns user from uid, db proxy now """
    return db.get_user_from_uid(uid)


@cache.memoize(300)
def getDomain(link):
    """ Gets Domain from url """
    x = urlparse(link)
    return x.netloc


@cache.memoize(300)
def isImage(link):
    """ Returns True if link ends with img suffix """
    suffix = ('.png', '.jpg', '.gif', '.tiff', '.bmp')
    return link.lower().endswith(suffix)


@cache.memoize(300)
def isGifv(link):
    """ Returns True if link ends with video suffix """
    domains = ['imgur.com', 'i.imgur.com', 'i.sli.mg', 'sli.mg']
    if link.lower().endswith('.gifv'):
        for domain in domains:
            if domain in link.lower():
                return True
    else:
        return False


@cache.memoize(300)
def isVideo(link):
    """ Returns True if link ends with video suffix """
    suffix = ('.mp4', '.webm')
    return link.lower().endswith(suffix)


@cache.memoize(30)
def get_comment_score(comment):
    """ Returns the score for comment """
    return comment['score'] if comment['score'] else 0
