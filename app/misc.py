""" Misc helper function and classes. """
from urllib.parse import urlparse, parse_qs
import json
import math
import uuid
import time
import os
import hashlib
import re
from datetime import datetime, timedelta
from io import BytesIO
from PIL import Image
from bs4 import BeautifulSoup
from functools import update_wrapper
import misaka as m
from redis import Redis
import sendgrid
import config
from flask import url_for, request, g, jsonify
from flask_login import AnonymousUserMixin, current_user
from .caching import cache
from . import database as db
from .badges import badges

from .models import Sub, SubPost, User, SiteMetadata, SubSubscriber, Message, UserMetadata
from .models import SubPostVote, MiningLeaderboard, SubPostComment, SubPostCommentVote
from .models import MiningSpeedLeaderboard, SubMetadata, rconn
from peewee import JOIN, fn, Clause, SQL
import requests

redis = Redis(host=config.CACHE_REDIS_HOST,
              port=config.CACHE_REDIS_PORT,
              db=config.CACHE_REDIS_DB)

# Regex that matches VALID user and sub names
allowedNames = re.compile("^[a-zA-Z0-9_-]+$")


class SiteUser(object):
    """ Representation of a site user. Used on the login manager. """

    def __init__(self, userclass=None, subs=[]):
        self.user = userclass
        self.notifications = self.user['notifications']
        self.name = self.user['name']
        self.uid = self.user['uid']
        self.prefs = self.user['prefs'].split(',') if self.user['prefs'] else []

        self.subsid = []
        self.subscriptions = []
        self.blocksid = []
        for i in subs:
            if i['status'] == 1:
                self.subscriptions.append(i['name'])
                self.subsid.append(i['sid'])
            else:
                self.blocksid.append(i['sid'])

        self.score = self.user['score']
        self.given = self.user['given']
        # If status is not 0, user is banned
        if self.user['status'] != 0:
            self.is_active = False
        else:
            self.is_active = True
        if self.user:
            self.is_authenticated = True
            self.is_anonymous = False
            self.admin = 'admin' in self.prefs
        else:
            self.is_authenticated = False
            self.is_anonymous = True

    def __repr__(self):
        return "<SiteUser {0}>".format(self.uid)

    def get_id(self):
        """ Returns the unique user id. Used on load_user """
        return self.uid

    def get_username(self):
        """ Returns the user name. Used on load_user """
        return self.name

    def is_mod(self, sid):
        """ Returns True if the current user is a mod of 'sub' """
        return isMod(sid, self.uid)

    def is_subban(self, sub):
        """ Returns True if the current user is banned from 'sub' """
        return isSubBan(sub, self.user)

    def is_modinv(self, sub):
        """ Returns True if the current user is invited to mod of 'sub' """
        return isModInv(sub, self.user)

    def is_admin(self):
        """ Returns true if the current user is a site admin. """
        return self.admin

    @cache.memoize(5)
    def get_blocked(self):
        ib = db.get_user_blocked(self.uid)
        return [x['sid'] for x in ib]

    def is_topmod(self, sub):
        """ Returns True if the current user is a mod of 'sub' """
        return isTopMod(sub, self.user)

    def has_mail(self):
        """ Returns True if the current user has unread messages """
        return (self.notifications > 0)

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

    def has_subscribed(self, name):
        """ Returns True if the current user has subscribed to sub """
        return name in self.subscriptions

    def has_blocked(self, sid):
        """ Returns True if the current user has blocked sub """
        x = db.query('SELECT xid FROM `sub_subscriber` '
                     'WHERE `sid`=%s AND `uid`=%s AND `status`=%s',
                     (sid, self.uid, 2))
        return bool(x.fetchone())

    def new_count(self):
        """ Returns new message count """
        return self.notifications

    def has_exlinks(self):
        """ Returns true if user selects to open links in a new window """
        x = db.get_user_metadata(self.uid, 'exlinks')
        if x:
            return True if x == '1' else False
        else:
            return False

    def likes_scroll(self):
        """ Returns true if user likes scroll """
        return 'noscroll' not in self.prefs

    def block_styles(self):
        """ Returns true if user selects to block sub styles """
        return 'nostyles' in self.prefs

    def show_nsfw(self):
        """ Returns true if user selects show nsfw posts """
        return 'nsfw' in self.prefs

    @cache.memoize(300)
    def get_post_score(self):
        """ Returns the post vote score of a user. """
        return get_user_post_score(self.user)

    @cache.memoize(300)
    def get_post_score_counts(self):
        """ Returns the post vote score of a user. """
        return get_user_post_score_counts(self.user)

    @cache.memoize(300)
    def get_user_level(self):
        """ Returns the level and xp of a user. """
        return get_user_level(self.uid)

    @cache.memoize(120)
    def get_post_voting(self):
        """ Returns the post voting for a user. """
        return db.get_user_post_voting(self.uid)

    def get_subscriptions(self):
        return self.subscriptions


class SiteAnon(AnonymousUserMixin):
    """ A subclass of AnonymousUserMixin. Used for logged out users. """
    uid = False
    subsid = []
    subscriptions = []
    blocksid = []
    prefs = []
    admin = False

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
    def likes_scroll(cls):
        """ Anons like scroll. """
        return True

    @classmethod
    def get_blocked(cls):
        return []

    def get_subscriptions(self):
        return getDefaultSubs_list()

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
    def is_labrat(cls):
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


class RateLimit(object):
    """ This class does the rate-limit magic """
    expiration_window = 10

    def __init__(self, key_prefix, limit, per, send_x_headers):
        self.reset = (int(time.time()) // per) * per + per
        self.key = key_prefix + str(self.reset)
        self.limit = limit
        self.per = per
        self.send_x_headers = send_x_headers
        p = redis.pipeline()
        p.incr(self.key)
        p.expireat(self.key, self.reset + self.expiration_window)
        self.current = min(p.execute()[0], limit)

    remaining = property(lambda x: x.limit - x.current)
    over_limit = property(lambda x: x.current >= x.limit)


def get_view_rate_limit():
    """ Returns the rate limit for the current view """
    return getattr(g, '_view_rate_limit', None)


def on_over_limit(limit):
    """ This is called when the rate limit is reached """
    return jsonify(status='error', error=['Whoa, calm down and wait a '
                                          'bit before posting again.'])


def get_ip():
    """ Tries to return the user's actual IP address. """
    if request.access_route:
        return request.access_route[-1]
    else:
        return request.remote_addr


def ratelimit(limit, per=300, send_x_headers=True,
              over_limit=on_over_limit,
              scope_func=lambda: get_ip(),
              key_func=lambda: request.endpoint):
    """ This is a decorator. It does the rate-limit magic. """
    def decorator(f):
        """ Function inside function! """
        def rate_limited(*args, **kwargs):
            """ FUNCTIONCEPTION """
            key = 'rate-limit/%s/%s/' % (key_func(), scope_func())
            rlimit = RateLimit(key, limit + 1, per, send_x_headers)
            g._view_rate_limit = rlimit
            if over_limit is not None and rlimit.over_limit:
                if not g.appconfig.get('TESTING'):
                    return over_limit(rlimit)
            return f(*args, **kwargs)
        return update_wrapper(rate_limited, f)
    return decorator


def safeRequest(url, recieve_timeout=10):
    """ Gets stuff for the internet, with timeouts and size restrictions """
    # Returns (Response, File)
    max_size = 25000000  # won't download more than 25MB
    r = requests.get(url, stream=True, timeout=recieve_timeout)
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


RE_AMENTION = re.compile(r'(?:(\[.+?\]\(.+?\))|(?<=^|(?<=[^a-zA-Z0-9-_\.]))((@|\/u\/|\/s\/)([A-Za-z0-9\-\_]+)))')


class PhuksDown(m.SaferHtmlRenderer):
    _allowed_url_re = re.compile(r'^(https?:|\/)', re.I)

    def image(self, raw_url, title='', alt=''):
        return False

    def check_url(self, url, is_image_src=False):
        return bool(self._allowed_url_re.match(url))


md = m.Markdown(PhuksDown(sanitization_mode='escape'),
                extensions=['tables', 'fenced-code', 'autolink', 'strikethrough',
                            'superscript'])


def our_markdown(text):
    """ Here we create a custom markdown function where we load all the
    extensions we need. """
    def repl(match):
        if match.group(3) is None:
            return match.group(0)

        if match.group(3) == '@':
            ln = '/u/' + match.group(4)
        else:
            ln = match.group(2)
        return '[{0}]({1})'.format(match.group(2), ln)
    text = RE_AMENTION.sub(repl, text)
    try:
        return md(text)
    except RecursionError:
        return '> tfw tried to break the site'


@cache.memoize(5)
def getVoteStatus(uid, pid):
    """ Returns if the user voted positively or negatively to a post """
    if not uid:
        return -1

    c = db.query('SELECT positive FROM `sub_post_vote` WHERE `uid`=%s'
                 ' AND `pid`=%s', (uid, pid, ))
    vote = c.fetchone()
    if not vote:
        return -1
    return int(vote['positive'])


@cache.memoize(20)
def get_post_upcount(pid):
    """ Returns the upvote count """
    c = db.query('SELECT positive FROM `sub_post_vote` WHERE '
                 '`pid`=%s', (pid, ))
    score = 0
    for i in c.fetchall():
        if i['positive']:
            score += 1
    return score


@cache.memoize(20)
def get_post_downcount(pid):
    """ Returns the downvote count """
    c = db.query('SELECT positive FROM `sub_post_vote` WHERE '
                 '`pid`=%s', (pid, ))
    score = 0
    for i in c.fetchall():
        if not i['positive']:
            score += 1
    return score


@cache.memoize(20)
def get_comment_voting(cid):
    """ Returns a tuple with the up/downvote counts """
    c = db.query('SELECT positive FROM `sub_post_comment_vote` WHERE '
                 '`cid`=%s', (cid, ))
    upvote = 0
    downvote = 0
    for i in c.fetchall():
        if i['positive']:
            upvote += 1
        else:
            downvote += 1
    return (upvote, downvote)


@cache.memoize(50)
def hasVotedComment(uid, comment, up=True):
    # TODO: blast this from orbit
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
    return db.get_sub_from_pid(db.get_comment_from_cid(cid)['pid'])


def isMod(sid, uid):
    """ Returns True if 'user' is a mod of 'sub' """
    x = db.get_sub_metadata(sid, 'mod1', value=uid)
    if x:
        return True

    x = db.get_sub_metadata(sid, 'mod2', value=uid)
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


@cache.memoize(20)
def getSubTimer(sub):
    """ Returns the sub's timer time metadata """
    x = db.get_sub_metadata(sub['sid'], 'timer')
    if x:
        return x['value']
    else:
        return False


@cache.memoize(600)
def getSubTimerMsg(sub):
    """ Returns the sub's timer msg metadata """
    x = db.get_sub_metadata(sub['sid'], 'timermsg')
    if x:
        return x['value']
    else:
        return False


@cache.memoize(600)
def getShowSubTimer(sub):
    """ Returns true if show sub timer """
    x = db.get_sub_metadata(sub['sid'], 'showtimer')
    return False if not x or x == '0' else True


@cache.memoize(6)
def getSubTags(sub):
    """ Returns sub tags for form """
    x = db.uquery('Select `value` FROM `sub_metadata` WHERE `key`=%s '
                  'AND `sid`=%s', ('tag', sub['sid']))
    i = ''
    for y in x:
        i += str(y['value']) + '+'
    return str(i)[:-1]


@cache.memoize(60)
def getSubTagsSearch(page, term):
    """ Returns sub tags search for subs page """
    c = db.query('SELECT * FROM `sub_metadata` WHERE `key`=%s AND `value` LIKE %s '
                 ' LIMIT %s ,30',
                 ('tag', term, (page - 1) * 30))
    subs = []
    for i in c.fetchall():
        sub = db.get_sub_from_sid(i['sid'])
        if sub not in subs:
            subs.append(sub)
    return subs


@cache.memoize(60)
def getSubTagsSidebar():
    """ Returns sub tags subs page sidebar"""
    c = db.query('SELECT * FROM `sub_metadata` WHERE `key`=%s ',
                 ('tag', ))
    tags = []
    for i in c.fetchall():
        if i['value'] not in tags:
            tags.append(i['value'])
    # tags = list(set(tags))  # random
    tags = sorted(tags, key=str.lower)  # alphabetical
    return tags


@cache.memoize(6)
def getSubTagsList(sub):
    """ Returns sub tags for edit sub page """
    x = db.uquery('Select `value` FROM `sub_metadata` WHERE `key`=%s '
                  'AND `sid`=%s', ('tag', sub['sid']))
    return x.fetchall()


@cache.memoize(600)
def getSubCreation(sub):
    """ Returns the sub's 'creation' metadata """
    x = db.get_sub_metadata(sub['sid'], 'creation')
    try:
        return x['value'].replace(' ', 'T')  # Converts to ISO format
    except TypeError:  # no sub creation!
        return ''


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
    y = db.query('SELECT COUNT(*) AS c FROM `sub_post` WHERE `sid`=%s',
                 (sub['sid'],)).fetchone()['c']
    return y


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


def getPostFlair(post):
    """ Returns true if the post has available flair """
    return post['flair']


@cache.memoize(600)
def getDefaultSubs():
    """ Returns a list of all the default subs """
    md = db.get_site_metadata('default', True)
    defaults = []
    for sub in md:
        defaults.append({'sid': sub['value']})
    return defaults


@cache.memoize(600)
def getDefaultSubs_list():
    """ Returns a list of all the default subs """
    md = db.get_site_metadata('default', True)
    defaults = []
    for i in md:
        sub = db.get_sub_from_sid(i['value'])
        defaults.append(sub['name'])
    defaults = sorted(defaults, key=str.lower)
    return defaults


def getSubscriptions(uid):
    """ Returns all the subs the current user is subscribed to """
    if uid:
        subs = db.get_user_subscriptions(uid)
    else:
        subs = getDefaultSubs()
    return list(subs)


def getSubscriptions_list(uid):
    """ Returns all the subs the current user is subscribed to """
    if uid:
        subs = db.get_user_subscriptions_list(uid)
    else:
        subs = getDefaultSubs_list()
    return list(subs)


@cache.memoize(600)
def enableBTCmod():
    """ Returns true if BTC donation module is enabled """
    x = db.get_site_metadata('usebtc')
    return False if not x or x['value'] == '0' else True


def enableInviteCode():
    """ Returns true if invite code is required to register """
    x = db.get_site_metadata('useinvitecode')
    return False if not x or x['value'] == '0' else True


def getInviteCode():
    """ Returns invite code """
    x = db.get_site_metadata('invitecode')
    if x:
        return x['value']


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
def getPostsFromSubs(subs, limit=False, orderby='pid', paging=False, inj=''):
    """ Returns all posts from a list or subs """
    if not subs:
        return []
    qbody = "SELECT * FROM `sub_post` WHERE `sid` IN ("
    qdata = []
    for sub in subs:
        qbody += "%s,"
        qdata.append(sub['sid'])
    qbody = qbody[:-1] + ') '
    qbody += inj  # whee
    qbody += ' ORDER BY `' + orderby + '` DESC'
    if limit is not False:
        qbody += ' LIMIT %s'
        qdata.append(limit)
        if paging:
            qbody += ',%s'
            qdata.append(paging)
    c = db.query(qbody, qdata)

    return c.fetchall()


@cache.memoize(120)
def getPostsFromPids(pids, limit=False, orderby='pid'):
    """ Returns all posts from a list of pids """
    if not pids:
        return []
    qbody = "SELECT * FROM `sub_post` WHERE "
    qdata = []
    for post in pids:
        qbody += "`pid`=%s OR "
        qdata.append(post['pid'])
    qbody = qbody[:-4] + ' ORDER BY %s'
    qdata.append(orderby)
    if limit:
        qbody += ' LIMIT %s'
        qdata.append(limit)
    c = db.query(qbody, tuple(qdata))
    return c.fetchall()


def workWithMentions(data, receivedby, post, sub):
    """ Does all the job for mentions """
    mts = re.findall(RE_AMENTION, data)
    if mts:
        mts = list(set(mts))  # Removes dupes
        # Filter only users
        mts = [x[3] for x in mts if x[2] == "/u/" or x[2] == "@"]
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


def getDomain(link):
    """ Gets Domain from url """
    x = urlparse(link)
    return x.netloc


@cache.memoize(300)
def isImage(link):
    """ Returns True if link ends with img suffix """
    suffix = ('.png', '.jpg', '.gif', '.tiff', '.bmp', '.jpeg')
    return link.lower().endswith(suffix)


@cache.memoize(300)
def isGifv(link):
    """ Returns True if link ends with video suffix """
    return link.lower().endswith('.gifv')


@cache.memoize(300)
def isVideo(link):
    """ Returns True if link ends with video suffix """
    suffix = ('.mp4', '.webm')
    return link.lower().endswith(suffix)


def get_user_post_score(user):
    """ Returns the user's post score """
    if user['score'] is None:
        mposts = db.query('SELECT * FROM `sub_post` WHERE `uid`=%s',
                          (user['uid'], )).fetchall()

        q = "SELECT `positive` FROM `sub_post_vote` WHERE `pid` IN ("
        lst = []
        for post in mposts:
            q += '%s, '
            lst.append(post['pid'])
        q = q[:-2] + ")"
        count = 0

        if lst:
            votes = db.query(q, list(lst)).fetchall()

            for vote in votes:
                if vote['positive']:
                    count += 1
                else:
                    count -= 1

        mposts = db.query('SELECT * FROM `sub_post_comment` WHERE '
                          '`uid`=%s', (user['uid'], )).fetchall()
        q = "SELECT `positive` FROM `sub_post_comment_vote`"
        q += " WHERE `cid` IN ("

        lst = []
        for post in mposts:
            q += '%s, '
            lst.append(post['cid'])
        q = q[:-2] + ")"

        if lst:
            votes = db.query(q, list(lst)).fetchall()

            for vote in votes:
                if vote['positive']:
                    count += 1
                else:
                    count -= 1

        db.uquery('UPDATE `user` SET `score`=%s WHERE `uid`=%s',
                  (count, user['uid']))
        return count
    return user['score']


@cache.memoize(300)
def get_user_post_score_counts(user):
    """ Returns the user's post and comment scores """
    count = 0
    postpos = 0
    postneg = 0
    commpos = 0
    commneg = 0
    mposts = db.query('SELECT * FROM `sub_post` WHERE `uid`=%s',
                      (user['uid'], )).fetchall()

    q = "SELECT `positive` FROM `sub_post_vote` WHERE `pid` IN ("
    lst = []
    for post in mposts:
        q += '%s, '
        lst.append(post['pid'])
    q = q[:-2] + ")"
    if lst:
        votes = db.query(q, list(lst)).fetchall()

        for vote in votes:
            if vote['positive']:
                count += 1
                postpos += 1
            else:
                count -= 1
                postneg += 1

    mposts = db.query('SELECT * FROM `sub_post_comment` WHERE '
                      '`uid`=%s', (user['uid'], )).fetchall()
    q = "SELECT `positive` FROM `sub_post_comment_vote`"
    q += " WHERE `cid` IN ("

    lst = []
    for post in mposts:
        q += '%s, '
        lst.append(post['cid'])
    q = q[:-2] + ")"
    if lst:
        votes = db.query(q, list(lst)).fetchall()

        for vote in votes:
            if vote['positive']:
                count += 1
                commpos += 1
            else:
                count -= 1
                commneg += 1

    db.uquery('UPDATE `user` SET `score`=%s WHERE `uid`=%s',
              (count, user['uid']))
    score = count
    return (score, postpos, postneg, commpos, commneg)


@cache.memoize(10)
def get_user_level(uid):
    """ Returns the user's level and XP as a tuple (level, xp) """
    user = db.get_user_from_uid(uid)
    xp = get_user_post_score(user)
    # xp += db.get_user_post_voting(uid)/2
    badges = getUserBadges(uid)
    for badge in badges:
        xp += badge['score']
    if xp <= 0:  # We don't want to do the sqrt of a negative number
        return (0, xp)
    level = math.sqrt(xp / 10)
    return (int(level), xp)


def _image_entropy(img):
    """calculate the entropy of an image"""
    hist = img.histogram()
    hist_size = sum(hist)
    hist = [float(h) / hist_size for h in hist]

    return -sum(p * math.log(p, 2) for p in hist if p != 0)


THUMB_NAMESPACE = uuid.UUID('f674f09a-4dcf-4e4e-a0b2-79153e27e387')


def get_thumbnail(form):
    """ Tries to fetch a thumbnail """
    # 1 - Check if it's an image
    try:
        req = safeRequest(form.link.data)
    except (requests.exceptions.RequestException, ValueError):
        return ''
    ctype = req[0].headers.get('content-type', '').split(";")[0].lower()
    good_types = ['image/gif', 'image/jpeg', 'image/png']
    if ctype in good_types:
        # yay, it's an image!!1
        # Resize
        im = Image.open(BytesIO(req[1])).convert('RGB')
    elif ctype == 'text/html':
        # Not an image!! Let's try with OpenGraph
        og = BeautifulSoup(req[1], 'lxml')
        try:
            img = og('meta', {'property': 'og:image'})[0].get('content')
            req = safeRequest(img)
        except (OSError, ValueError, IndexError):
            # no image
            return ''
        im = Image.open(BytesIO(req[1])).convert('RGB')
    else:
        return ''

    x, y = im.size
    while y > x:
        slice_height = min(y - x, 10)
        bottom = im.crop((0, y - slice_height, x, y))
        top = im.crop((0, 0, x, slice_height))

        if _image_entropy(bottom) < _image_entropy(top):
            im = im.crop((0, 0, x, y - slice_height))
        else:
            im = im.crop((0, slice_height, x, y))

        x, y = im.size

    im.thumbnail((70, 70), Image.ANTIALIAS)

    im.seek(0)
    md5 = hashlib.md5(im.tobytes())
    filename = str(uuid.uuid5(THUMB_NAMESPACE, md5.hexdigest())) + '.jpg'
    im.seek(0)
    if not os.path.isfile(os.path.join(config.THUMBNAILS, filename)):
        im.save(os.path.join(config.THUMBNAILS, filename), "JPEG")
    im.close()

    return filename

# -----------------------------------
# Stuff after this line was checked™
# -----------------------------------


@cache.memoize(300)
def getTodaysTopPosts():
    """ Returns top posts in the last 24 hours """
    td = datetime.utcnow() - timedelta(days=1)
    posts = (SubPost.select(SubPost.pid, Sub.name.alias('sub'), SubPost.title, SubPost.posted, SubPost.score)
                    .where(SubPost.posted > td).order_by(SubPost.score.desc()).limit(5)
                    .join(Sub, JOIN.LEFT_OUTER).dicts())
    top_posts = []
    for p in posts:
        top_posts.append(p)
    return top_posts


def getRandomSub():
    """ Returns a random sub for index sidebar """
    try:
        sub = Sub.select(Sub.sid, Sub.name, Sub.title).order_by(fn.Rand()).dicts().get()
    except Sub.DoesNotExist:
        return False
    return sub


@cache.memoize(10)
def getSubOfTheDay():
    daysub = rconn.get('daysub')
    if not daysub:
        try:
            daysub = Sub.select(Sub.sid, Sub.name, Sub.title).order_by(fn.Rand()).get()
        except Sub.DoesNotExist:  # No subs
            return False
        today = datetime.utcnow()
        tomorrow = datetime(year=today.year, month=today.month, day=today.day) + timedelta(seconds=86400)
        timeuntiltomorrow = tomorrow - today
        rconn.setex('daysub', daysub.sid, timeuntiltomorrow)
    else:
        try:
            daysub = Sub.select(Sub.name, Sub.title).where(Sub.sid == daysub).get()
        except Sub.DoesNotExist:  # ???
            return False


def getChangelog():
    """ Returns most recent changelog post """
    td = datetime.utcnow() - timedelta(days=15)
    changepost = (SubPost.select(Sub.name.alias('sub'), SubPost.pid, SubPost.title, SubPost.posted)
                         .where(SubPost.posted > td).where(SubPost.sid == config.CHANGELOG_SUB)
                         .join(Sub, JOIN.LEFT_OUTER).dicts())

    try:
        return changepost.get()
    except SubPost.DoesNotExist:
        return None


def getSinglePost(pid):
    if current_user.is_authenticated:
        posts = SubPost.select(SubPost.nsfw, SubPost.content, SubPost.pid, SubPost.title, SubPost.posted, SubPost.score,
                               SubPost.thumbnail, SubPost.link, User.name.alias('user'), Sub.name.alias('sub'), SubPost.flair,
                               SubPost.comments, SubPostVote.positive, User.uid, *extra)
        posts = posts.join(SubPostVote, JOIN.LEFT_OUTER, on=((SubPostVote.pid == SubPost.pid) & (SubPostVote.uid == current_user.uid))).switch(SubPost)
    else:
        posts = SubPost.select(SubPost.nsfw, SubPost.content, SubPost.pid, SubPost.title, SubPost.posted, SubPost.score,
                               SubPost.thumbnail, SubPost.link, User.name.alias('user'), Sub.name.alias('sub'), SubPost.flair,
                               SubPost.comments, User.uid, *extra)
    posts = posts.join(User, JOIN.LEFT_OUTER).switch(SubPost).join(Sub, JOIN.LEFT_OUTER).where(SubPost.pid == pid).dicts().get()



def postListQueryBase(*extra, nofilter=False, noAllFilter=False, noDetail=False):
    if current_user.is_authenticated and not noDetail:
        posts = SubPost.select(SubPost.nsfw, SubPost.content, SubPost.pid, SubPost.title, SubPost.posted, SubPost.score,
                               SubPost.thumbnail, SubPost.link, User.name.alias('user'), Sub.name.alias('sub'), SubPost.flair,
                               SubPost.comments, SubPostVote.positive, User.uid, *extra)
        posts = posts.join(SubPostVote, JOIN.LEFT_OUTER, on=((SubPostVote.pid == SubPost.pid) & (SubPostVote.uid == current_user.uid))).switch(SubPost)
    else:
        posts = SubPost.select(SubPost.nsfw, SubPost.content, SubPost.pid, SubPost.title, SubPost.posted, SubPost.score,
                               SubPost.thumbnail, SubPost.link, User.name.alias('user'), Sub.name.alias('sub'), SubPost.flair,
                               SubPost.comments, User.uid, *extra)
    posts = posts.join(User, JOIN.LEFT_OUTER).switch(SubPost).join(Sub, JOIN.LEFT_OUTER)
    posts = posts.where(SubPost.deleted == 0)
    if not noAllFilter and not nofilter:
        if current_user.is_authenticated and current_user.blocksid:
            posts = posts.where(SubPost.sid.not_in(current_user.blocksid))
    if (not nofilter) and ((not current_user.is_authenticated) or ('nsfw' not in current_user.prefs)):
        posts = posts.where(SubPost.nsfw == 0)
    return posts


def postListQueryHome(noDetail=False, nofilter=False):
    if current_user.is_authenticated:
        return (postListQueryBase(noDetail=noDetail, nofilter=nofilter).where(SubPost.sid << current_user.subsid))
    else:
        return postListQueryBase(noDetail=noDetail, nofilter=nofilter).join(SiteMetadata, JOIN.LEFT_OUTER, on=(SiteMetadata.key == 'default')).where(SubPost.sid == SiteMetadata.value)


def getPostList(baseQuery, sort, page):
    if sort == "hot":
        posts = baseQuery.order_by((SubPost.score * 20 + (SubPost.posted - 1134028003) / 5000).desc()).limit(100).paginate(page, 25)
    elif sort == "top":
        posts = baseQuery.order_by(SubPost.score.desc()).paginate(page, 25)
    elif sort == "new":
        posts = baseQuery.order_by(SubPost.pid.desc()).paginate(page, 25)
    return posts


@cache.memoize(600)
def getAnnouncement():
    """ Returns sitewide announcement post or False """
    try:
        ann = SiteMetadata.select().where(SiteMetadata.key == 'announcement').get()
        if not ann.value:
            return False
        return postListQueryBase(nofilter=True).where(SubPost.pid == ann.value).dicts().get()
    except SiteMetadata.DoesNotExist:
        return False


@cache.memoize(5)
def getStickyPid(sid):
    """ Returns a list of stickied SubPosts """
    x = SubMetadata.select(SubMetadata.value).where(SubMetadata.sid == sid).where(SubMetadata.key == 'sticky').dicts()
    return [int(y['value']) for y in x]


def getStickies(sid):
    sp = getStickyPid(sid)
    posts = postListQueryBase().where(SubPost.pid << sp).dicts()
    return posts


def load_user(user_id):
    user = User.select(fn.Count(Clause(SQL('Distinct'), Message.mid)).alias('notifications'),
                       User.given, User.score, User.name, User.uid, User.status,
                       fn.GROUP_CONCAT(Clause(SQL('Distinct'), UserMetadata.key)).alias('prefs'))
    user = user.join(UserMetadata, JOIN.LEFT_OUTER, on=((UserMetadata.uid == User.uid) & (UserMetadata.value == 1) & (UserMetadata.key << ['admin', 'canupload', 'exlinks', 'nostyles', 'labrat', 'nsfw', 'noscroll']))).switch(User)
    user = user.join(Message, JOIN.LEFT_OUTER, on=((Message.receivedby == User.uid) & (Message.mtype != 6) & Message.read.is_null(True))).switch(User)
    user = user.where(User.uid == user_id).dicts()

    try:
        user = user.get()
        subs = SubSubscriber.select(SubSubscriber.sid, Sub.name, SubSubscriber.status).join(Sub, on=(Sub.sid == SubSubscriber.sid)).switch(SubSubscriber).where(SubSubscriber.uid == user_id).dicts()
        return SiteUser(user, subs)
    except User.DoesNotExist:
        return None


def get_errors(form):
    """ A simple function that returns a list with all the form errors. """
    if request.method == 'GET':
        return []
    ret = []
    for field, errors in form.errors.items():
        for error in errors:
            ret.append(u"Error in the '%s' field - %s" % (
                getattr(form, field).label.text,
                error))
    return ret


@cache.memoize(60)
def getCurrentHashrate():
    try:
        hr = safeRequest('https://supportxmr.com/api/miner/{0}/stats'.format(config.XMR_ADDRESS), 1)
        hr = json.loads(hr[1].decode())
        hr['amtDue'] = round(hr['amtDue'] / 1000000000000, 8)
        hr['amtPaid'] = round(hr['amtPaid'] / 1000000000000, 8)
        hr['hash'] = int(hr['hash'])
        hr['totalHashes'] = int(hr['totalHashes'])
        return hr
    except (ValueError, requests.RequestException) as err:
        return {'error': err}


@cache.memoize(60)
def getCurrentUserStats(username):
    try:
        x = MiningLeaderboard.select().where(MiningLeaderboard.username == username).get()
        return {'balance': x.score}
    except MiningLeaderboard.DoesNotExist:
        return {'balance': 0}


def getMiningLeaderboard():
    """ Get mining leaderboard """
    x = MiningLeaderboard.select().order_by(MiningLeaderboard.score.desc()).limit(10).dicts()
    return x


def getHPLeaderboard():
    """ Get mining leaderboard """
    x = MiningSpeedLeaderboard.select(MiningSpeedLeaderboard.username, MiningSpeedLeaderboard.hashes).order_by(MiningSpeedLeaderboard.hashes.desc()).limit(10).dicts()
    return x


@cache.memoize(60)
def getMiningLeaderboardJson():
    """ Get mining leaderboard """
    x = getMiningLeaderboard()
    z = getHPLeaderboard()
    f = []
    i = 1
    for user in x:
        user['rank'] = i
        user['score'] = "{:,}".format(user['score'])
        del user['xid']
        f.append(user)
        i += 1
    return {'users': f, 'speed': list(z)}


def build_comment_tree(comments, root=None):
    """ Creates the nested list structure for the comments """
    # 1. Group by parent
    parents = {}
    for comment in comments:
        try:
            parents[comment['parentcid']].append(comment['cid'])
        except KeyError:
            parents[comment['parentcid']] = [comment['cid']]

    getstuff = []  # list of cids we must fully fetch on the next pass.

    def do_the_needful(com, depth=0):
        # here we get all the child of com, iterate, etc
        if depth > 5:  # hard stop.
            return []
        f = []
        if parents.get(com, None) is not None:
            for k in parents[com]:
                if depth < 3:
                    getstuff.append(k)
                tmpnm = {'cid': k, 'children': do_the_needful(k, depth + 1)}
                ccount = len(tmpnm['children'])
                for k in tmpnm['children']:
                    ccount += k['ccount']
                tmpnm['ccount'] = ccount
                if len(tmpnm['children']) > 5:
                    tmpnm['moresiblings'] = len(tmpnm['children']) - 5
                    tmpnm['children'] = tmpnm['children'][:5]
                f.append(tmpnm)
        return f

    finct = []
    if len(parents[root]) > 8:
        tmpnm = {'cid': 0, 'moresiblings': len(parents[root]) - 8}
        parents[root] = parents[root][:8]
        finct.append(tmpnm)
    for ct in parents[root]:
        getstuff.append(ct)
        tmpnm = {'cid': ct, 'children': do_the_needful(ct)}
        if len(tmpnm['children']) > 5:
            tmpnm['moresiblings'] = len(tmpnm['children']) - 10
            tmpnm['children'] = tmpnm['children'][:5]
        else:
            finct.append(tmpnm)

    return (finct, getstuff)


def expand_comment_tree(comsx):
    coms = comsx[0]
    expcomms = SubPostComment.select(SubPostComment.cid, SubPostComment.content, SubPostComment.lastedit,
                                     SubPostComment.score, SubPostComment.status, SubPostComment.time, SubPostComment.pid,
                                     User.name.alias('username'), SubPostCommentVote.positive, SubPostComment.uid)
    expcomms = expcomms.join(User, on=(User.uid == SubPostComment.uid)).switch(SubPostComment)
    expcomms = expcomms.join(SubPostCommentVote, JOIN.LEFT_OUTER, on=((SubPostCommentVote.uid == current_user.get_id()) & (SubPostCommentVote.cid == SubPostComment.cid)))
    expcomms = expcomms.where(SubPostComment.cid << comsx[1]).dicts()
    lcomms = {}

    for k in expcomms:
        lcomms[k['cid']] = k

    def i_like_recursion(xm, depth=0):
        if depth == 2:
            return []
        ret = []
        for dom in xm:
            fmt = {**dom, **lcomms[dom['cid']]}
            if depth == 1 and len(fmt['children']) != 0:
                fmt['morechildren'] = True
            else:
                fmt['children'] = i_like_recursion(fmt['children'], depth=depth + 1)
            ret.append(fmt)
        return ret

    dcom = []
    for com in coms:
        if com['cid'] != 0:
            fmt = {**com, **lcomms[com['cid']]}
            fmt['children'] = i_like_recursion(fmt['children'])
            dcom.append(fmt)
        else:
            dcom.append(com)

    return dcom


def get_post_comments(pid):
    """ Returns the comments for a post `pid`"""
    cmskel = SubPostComment.select(SubPostComment.cid, SubPostComment.parentcid)
    cmskel = cmskel.where(SubPostComment.pid == pid).order_by(SubPostComment.score.desc()).dicts()

    if cmskel.count() == 0:
        return []

    cmxk = build_comment_tree(cmskel)
    return expand_comment_tree(cmxk)


# messages

def getMessagesIndex(page):
    """ Returns messages inbox """
    try:
        msg = Message.select(Message.mid, User.name.alias('username'), Message.receivedby, Message.subject, Message.content, Message.posted, Message.read, Message.mtype, Message.mlink)
        msg = msg.join(User, JOIN.LEFT_OUTER, on=(User.uid == Message.sentby)).where(Message.mtype << [1, 8]).where(Message.receivedby == current_user.get_id()).order_by(Message.mid.desc()).paginate(page, 20).dicts()
    except msg.DoesNotExist:
        return False
    return msg


def getMessagesSent(page):
    """ Returns messages sent """
    try:
        msg = Message.select(Message.mid, Message.sentby, User.name.alias('username'), Message.subject, Message.content, Message.posted, Message.read, Message.mtype, Message.mlink)
        msg = msg.join(User).where(Message.mtype == 1).where(Message.sentby == current_user.get_id()).order_by(Message.mid.desc()).paginate(page, 20).dicts()
    except msg.DoesNotExist:
        return False
    return msg


def getMessagesModmail(page):
    """ Returns modmail """
    try:
        msg = Message.select(Message.mid, User.name.alias('username'), Message.receivedby, Message.subject, Message.content, Message.posted, Message.read, Message.mtype, Message.mlink)
        msg = msg.join(User, on=(User.uid == Message.sentby)).where(Message.mtype << [2, 7]).where(Message.receivedby == current_user.get_id()).order_by(Message.mid.desc()).paginate(page, 20).dicts()
    except msg.DoesNotExist:
        return False
    return msg


def getMessagesSaved(page):
    """ Returns saved messages """
    try:
        msg = Message.select(Message.mid, User.name.alias('username'), Message.receivedby, Message.subject, Message.content, Message.posted, Message.read, Message.mtype, Message.mlink)
        msg = msg.join(User, on=(User.uid == Message.sentby)).where(Message.mtype == 9).where(Message.receivedby == current_user.get_id()).order_by(Message.mid.desc()).paginate(page, 20).dicts()
    except msg.DoesNotExist:
        return False
    return msg


def getMsgCommReplies(page):
    """ Returns comment replies messages """
    try:
        msg = Message.select(Message.mid, User.name.alias('username'), Message.receivedby, Message.subject, Message.content, Message.posted, Message.read, Message.mtype, Message.mlink)
        msg = msg.join(User, on=(User.uid == Message.sentby)).where(Message.mtype == 5).where(Message.receivedby == current_user.get_id()).order_by(Message.mid.desc()).paginate(page, 20).dicts()
    except msg.DoesNotExist:
        return False
    return msg


def getMsgPostReplies(page):
    """ Returns post replies messages """
    try:
        msg = Message.select(Message.mid, User.name.alias('username'), Message.receivedby, Message.subject, Message.content, Message.posted, Message.read, Message.mtype, Message.mlink)
        msg = msg.join(User, on=(User.uid == Message.sentby)).where(Message.mtype == 4).where(Message.receivedby == current_user.get_id()).order_by(Message.mid.desc()).paginate(page, 20).dicts()
    except msg.DoesNotExist:
        return False
    return msg


# user comments


def getUserComments(uid, page):
    """ Returns comments for a user """
    try:
        com = SubPostComment.select(Sub.name.alias('sub'), SubPost.title, SubPostComment.cid, SubPostComment.pid, SubPostComment.uid, SubPostComment.time, SubPostComment.lastedit, SubPostComment.content, SubPostComment.status, SubPostComment.score, SubPostComment.parentcid)
        com = com.join(SubPost).switch(SubPostComment).join(Sub, on=(Sub.sid == SubPost.sid))
        com = com.where(SubPostComment.uid == uid).where(SubPostComment.status.is_null()).order_by(SubPostComment.time.desc()).paginate(page, 20).dicts()
    except com.DoesNotExist:
        return False
    return com


def getUserBadges(uid):
    um = UserMetadata.select().where((UserMetadata.uid == uid) & (UserMetadata.key == 'badge')).dicts()
    ret = []
    for bg in um:
        if badges.get(bg['value']):
            ret.append(badges[bg['value']])
    return ret


def ktime0():
    print('bvo')
    g.boolkk = time.time()


def ktime():
    print('partial load: ', int((time.time() - g.boolkk) * 1000))
