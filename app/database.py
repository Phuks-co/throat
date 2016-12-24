""" All the database operations should be done from this file """
import uuid
import datetime
import bcrypt
import MySQLdb
import MySQLdb.cursors
import config
from flask import g
from .caching import cache


def connect_db(db=None):
    """Connects to the specific database."""
    if not db:
        db = g.appconfig['DB_NAME']

    rv = MySQLdb.connect(host=config.DB_HOST,
                         user=config.DB_USER,
                         passwd=config.DB_PASSWD,
                         db=db,
                         cursorclass=MySQLdb.cursors.DictCursor)
    return rv


def get_db():
    """Opens a new database connection if there is none yet for the
    current application context.
    """
    if not hasattr(g, 'db'):
        g.db = connect_db()
        g.qc = 0
    return g.db


def get_cursor():
    """ Returns a database cursor """
    db = get_db()
    return db.cursor()


def query(qr, params=()):
    """ Queries the database and returns the cursor """
    c = get_cursor()
    c.execute(qr, params)
    if not hasattr(g, 'qc'):
        g.qc = 0
    g.qc += 1
    return c


def uquery(qr, params=()):
    """ Queries the database to alter data """
    c = get_cursor()
    c.execute(qr, params)
    if not hasattr(g, 'qc'):
        g.qc = 0
    g.qc += 1
    g.dbmod = True
    return c


# Get X by id


@cache.memoize(10)
def get_user_from_uid(uid):
    """ Returns a user's db row from uid """
    c = query('SELECT * FROM `user` WHERE `uid`=%s', (uid, ))
    return c.fetchone()


@cache.memoize(10)
def get_user_from_name(name):
    """ Return a user's db row from the name """
    c = query('SELECT * FROM `user` WHERE `name`=%s', (name, ))
    return c.fetchone()


@cache.memoize(10)
def get_sub_from_pid(pid):
    """ Returns a sub's db info from a post's pid """
    c = query('SELECT `sid` FROM `sub_post` WHERE `pid`=%s', (pid, ))
    l = query('SELECT * FROM `sub` WHERE `sid`=%s', (c.fetchone()['sid'], ))
    return l.fetchone()


@cache.memoize(10)
def get_sub_from_name(name):
    """ Returns a sub's db info from the name """
    c = query('SELECT * FROM `sub` WHERE `name`=%s', (name, ))
    return c.fetchone()


@cache.memoize(10)
def get_sub_from_sid(sid):
    """ Returns a sub's db info from the sid """
    c = query('SELECT * FROM `sub` WHERE `sid`=%s', (sid, ))
    return c.fetchone()


@cache.memoize(10)
def get_post_from_pid(pid):
    """ Returns a post's db info from the pid """
    c = query('SELECT * FROM `sub_post` WHERE `pid`=%s', (pid, ))
    return c.fetchone()


@cache.memoize(5)
def get_comment_from_cid(cid):
    """ Returns a comment's db stuff from the cid """
    c = query('SELECT * FROM `sub_post_comment` WHERE `cid`=%s', (cid, ))
    return c.fetchone()

# Get X metadata


@cache.memoize(5)
def get_user_metadata(uid, key, _all=False):
    """ Gets user metadata. WARNING: THIS ONE DOES NOT RETURN THE RECORD """
    c = query('SELECT `key`,`value` FROM `user_metadata`'
              'WHERE `uid`=%s AND `key`=%s', (uid, key, ))
    if _all:
        return c.fetchall()
    else:
        v = c.fetchone()
        if v:
            return v['value']  # <=== DOES NOT RETURN RECORD
        else:
            return False


@cache.memoize(5)
def get_site_metadata(key, _all=False):
    """ Gets sitewide metadata """
    c = query('SELECT `value` FROM `site_metadata` WHERE `key`=%s', (key, ))
    if _all:
        return c.fetchall()
    else:
        return c.fetchone()


@cache.memoize(5)
def get_post_metadata(pid, key, _all=False):
    """ Gets post metadata """
    c = query('SELECT `value` FROM `sub_post_metadata` WHERE '
              '`key`=%s AND `pid`=%s', (key, pid))
    if _all:
        return c.fetchall()
    else:
        return c.fetchone()


@cache.memoize(5)
def get_sub_metadata(sid, key, _all=False, value=None):
    """ Gets sub metadata. If the value parameter is given, it returns True
    if the metadata entry has that value. """
    if not value:
        c = query('SELECT `value` FROM `sub_metadata` WHERE '
                  '`key`=%s AND `sid`=%s', (key, sid))
    else:
        c = query('SELECT `xid` FROM `sub_metadata` WHERE '
                  '`key`=%s AND `sid`=%s AND `value`=%s', (key, sid, value))
        if c.rowcount == 0:
            return False
        else:
            return True
    if _all:
        return c.fetchall()
    else:
        return c.fetchone()

# Create X metadata


def create_user_metadata(uid, key, value):
    """ Creates user metadata """
    uquery('INSERT INTO `user_metadata` (`uid`, `key`, `value`) '
           'VALUES (%s, %s, %s)', (uid, key, value))


def create_sub_metadata(sid, key, value):
    """ Creates sub metadata """
    uquery('INSERT INTO `sub_metadata` (`sid`, `key`, `value`) '
           'VALUES (%s, %s, %s)', (sid, key, value))


def create_post_metadata(pid, key, value):
    """ Creates sub metadata """
    uquery('INSERT INTO `sub_post_metadata` (`pid`, `key`, `value`) '
           'VALUES (%s, %s, %s)', (pid, key, value))


def create_site_metadata(key, value):
    """ Creates sub metadata """
    uquery('INSERT INTO `site_metadata` (`key`, `value`) VALUES (%s, %s)',
           (key, value))


# Update X metadata


def update_user_metadata(uid, key, value):
    """ Updates user metadata """
    x = get_user_metadata(uid, key)
    if not x:
        return create_user_metadata(uid, key, value)
    uquery('UPDATE `user_metadata` SET `value`=%s WHERE `uid`=%s '
           'AND `key`=%s', (value, uid, key))


def update_sub_metadata(sid, key, value):
    """ Updates user metadata """
    x = get_sub_metadata(sid, key)
    if not x:
        return create_sub_metadata(sid, key, value)
    uquery('UPDATE `sub_metadata` SET `value`=%s WHERE `sid`=%s '
           'AND `key`=%s', (value, sid, key))


def update_post_metadata(pid, key, value):
    """ Updates post metadata """
    x = get_post_metadata(pid, key)
    if not x:
        return create_post_metadata(pid, key, value)
    uquery('UPDATE `sub_post_metadata` SET `value`=%s WHERE `pid`=%s '
           'AND `key`=%s', (value, pid, key))


def update_site_metadata(key, value):
    """ Updates post metadata """
    x = get_site_metadata(key)
    if not x:
        return create_site_metadata(key, value)
    uquery('UPDATE `site_metadata` SET `value`=%s WHERE `key`=%s',
           (value, key))

# Create X


def create_user(username, email, password):
    """ Registers a user in the site """
    password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    if isinstance(password, bytes):
        password = password.decode('utf-8')
    uid = str(uuid.uuid4())
    joindate = datetime.datetime.utcnow()
    uquery('INSERT INTO `user` (`uid`, `name`, `password`, `email`, `crypto`, '
           '`status`, `joindate`, `score`) VALUES '
           '(%s, %s, %s, %s, 1, 0, %s, 0)', (uid, username, password, email,
                                             joindate))
    return {'uid': uid, 'name': username, 'password': password, 'email': email,
            'status': 0, 'crypto': 1, 'joindate': joindate, 'score': 0}


def create_sub(uid, name, title):
    """ Registers a new sub """
    sid = str(uuid.uuid4())
    uquery('INSERT INTO `sub` (`sid`, `name`, `title`, `sidebar`, `nsfw`) '
           'VALUES (%s, %s, %s, \'\', 0)', (sid, name, title))
    g.db.commit()
    create_sub_metadata(sid, 'mod', uid)
    create_sub_metadata(sid, 'mod1', uid)
    create_sub_metadata(sid, 'creation', datetime.datetime.utcnow())
    uquery('INSERT INTO `sub_stylesheet` (`sid`, `content`) VALUES (%s, %s)',
           (sid, '/* CSS here */'))
    return {'name': name, 'sid': sid}


def create_subscription(uid, sid, stype):
    """ Creates a user subscription """
    time = datetime.datetime.utcnow()
    uquery('INSERT INTO `sub_subscriber` (`time`, `uid`, `sid`, `status`) '
           'VALUES (%s, %s, %s, %s)', (time, uid, sid, stype))


def create_sitelog(action, description, link):
    """ Creates an entry in the site log """
    t = datetime.datetime.utcnow()
    uquery('INSERT INTO `site_log` (`time`, `action`, `desc`, `link`) VALUES '
           '(%s, %s, %s, %s)', (t, action, description, link))


def create_sublog(sid, action, description, link=''):
    """ Creates an entry in the site log """
    t = datetime.datetime.utcnow()
    uquery('INSERT INTO `sub_log` (`sid`, `time`, `action`, `desc`, `link`) '
           'VALUES (%s, %s, %s, %s, %s)', (sid, t, action, description, link))


def create_message(mfrom, to, subject, content, link, mtype):
    """ Creates a message. """
    posted = datetime.datetime.utcnow()
    uquery('INSERT INTO `message` (`sentby`, `receivedby`, `subject`, `mlink`'
           ', `content`, `posted`, `mtype`) VALUES (%s, %s, %s, %s, %s, %s, '
           '%s)', (mfrom, to, subject, link, content, posted, mtype))


def create_post(sid, uid, title, content, ptype, link=None, thumbnail=''):
    """ Duh. Creates a post """
    posted = datetime.datetime.utcnow()
    l = uquery('INSERT INTO `sub_post` (`sid`, `uid`, `title`, `link`, '
               '`posted`, `ptype`, `score`, `thumbnail`, `deleted`, `nsfw`, '
               '`content`) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, '
               '%s)', (sid, uid, title, link, posted, ptype, 1, thumbnail, 0,
                       0, content))
    g.db.commit()  # We insta-commit posts so we can safely edit thumbnail
    return {'sid': sid, 'uid': uid, 'link': link, 'posted': posted,
            'ptype': ptype, 'pid': l.lastrowid, 'title': title}


def create_comment(pid, uid, content, parentcid):
    """ Creates a comment """
    posted = datetime.datetime.utcnow()
    cid = str(uuid.uuid4())
    if parentcid == "0":
        parentcid = None
    l = uquery('INSERT INTO `sub_post_comment` (`uid`, `pid`, `time`, `score`,'
               ' `content`, `parentcid`, `cid`) VALUES (%s, %s, %s, %s, %s, '
               '%s, %s)', (uid, pid, posted, 0, content, parentcid, cid))
    g.db.commit()
    return {'pid': pid, 'uid': uid, 'cid': l.lastrowid}


def create_badge(badge, name, text):
    """ Creates a badge """
    bid = str(uuid.uuid4())
    uquery('INSERT INTO `user_badge` (`bid`, `badge`, `name`, `text`) '
           'VALUES (%s, %s, %s, %s)', (bid, badge, name, text))


@cache.memoize(10)
def get_sub_stylesheet(sid):
    """ Returns a sub's stylesheet from the sid """
    c = query('SELECT `content` FROM `sub_stylesheet` WHERE `sid`=%s', (sid, ))
    return c.fetchone()['content']


@cache.memoize(10)
def get_user_subscriptions(uid):
    """ Returns all the user's subscriptions from the uid """
    c = query('SELECT * FROM `sub_subscriber` WHERE `uid`=%s', (uid, ))
    return c.fetchall()


@cache.memoize(10)
def get_user_post_voting(uid):
    """ Returns the user's total voting score """
    c = query('SELECT positive FROM `sub_post_vote` WHERE `uid`=%s',
              (uid, ))
    l = c.fetchall()
    score = 0
    for i in l:
        if i['positive']:
            score += 1
        else:
            score -= 1
    return score


@cache.memoize(10)
def user_mail_count(uid):
    """ Returns the number of unread messages of a user """
    c = query('SELECT COUNT(*) FROM `message` WHERE `receivedby`=%s AND'
              '`mtype`!=6 AND `read` IS NULL', (uid, ))
    return c.fetchone()['COUNT(*)']


@cache.memoize(5)
def get_post_comment_count(pid):
    """ Returns a post's comment count """
    c = query('SELECT COUNT(*) FROM `sub_post_comment` WHERE `pid`=%s', (pid,))
    return c.fetchone()['COUNT(*)']


@cache.memoize(15)
def is_post_deleted(post):
    """ Returns true if a post was deleted """
    # XXX: Compatibility code
    if post['deleted'] is None:
        d1 = get_post_metadata(post['pid'], 'deleted')
        if d1:
            uquery('UPDATE `sub_post` SET `deleted`=%s WHERE `pid`=%s',
                   (1, post['pid']))
            return True
        d2 = get_post_metadata(post['pid'], 'moddeleted')
        if d2:
            uquery('UPDATE `sub_post` SET `deleted`=%s WHERE `pid`=%s',
                   (1, post['pid']))
            return True
        uquery('UPDATE `sub_post` SET `deleted`=%s WHERE `pid`=%s',
               (0, post['pid']))
        return False
    return post['deleted']


@cache.memoize(15)
def is_post_nsfw(post):
    """ Returns True if a post is marked as NSFW """
    # XXX: Compatibility code
    if post['nsfw'] is None:
        d1 = get_post_metadata(post['pid'], 'nsfw')
        if d1:
            if not d1['value']:
                d1['value'] = 0
            uquery('UPDATE `sub_post` SET `nsfw`=%s WHERE `pid`=%s',
                   (d1['value'], post['pid']))
            return bool(int(d1['value']))
        uquery('UPDATE `sub_post` SET `nsfw`=%s WHERE `pid`=%s',
               (0, post['pid']))
        return False
    return bool(post['nsfw'])


@cache.memoize(15)
def is_sub_nsfw(sub):
    """ Returns True if a sub was marked as NSFW """
    # XXX: Compatibility code
    if sub['nsfw'] is None:
        d1 = get_sub_metadata(sub['sid'], 'nsfw')
        if d1:
            uquery('UPDATE `sub` SET `nsfw`=%s WHERE `sid`=%s',
                   (d1['value'], sub['sid']))
            return d1['value']
        uquery('UPDATE `sub` SET `nsfw`=%s WHERE `sid`=%s',
               (0, sub['sid']))
        return False
    return sub['nsfw']


@cache.memoize(300)
def get_post_thumbnail(post):
    """ Returns the post's thumbnail """
    # XXX: Compatibility code
    if post['thumbnail'] is None:
        d1 = get_post_metadata(post['pid'], 'thumbnail')
        if d1:
            uquery('UPDATE `sub_post` SET `thumbnail`=%s WHERE `pid`=%s',
                   (d1['value'], post['pid']))
            return d1['value']
        uquery('UPDATE `sub_post` SET `thumbnail`=%s WHERE `pid`=%s',
               ('', post['pid']))
        return ''
    return post['thumbnail']


@cache.memoize(10)
def get_post_comments(pid, parent=None):
    """ Returns some comments from a post. If the parentcid parameter is given,
    it returns all the child-comments from that cid. If not, it'll only return
    the root comments.  """
    q = 'SELECT * FROM `sub_post_comment` WHERE `pid`=%s'
    if parent:
        q += ' AND `parentcid`=%s'
        c = query(q, (pid, parent))
    else:
        q += ' AND `parentcid` IS NULL'
        c = query(q, (pid, ))

    return c.fetchall()


@cache.memoize(10)
def get_user_badges(uid):
    """ Returns all the user's badges. """
    badges = get_user_metadata(uid, 'badge', _all=True)
    b = []
    for i in badges:
        c = query('SELECT * FROM `user_badge` WHERE `bid`=%s', (i['value'],))
        b.append(c.fetchone())
    return b


@cache.memoize(10)
def get_user_positions(uid, pos):
    """ Returns a list of subs the user has `pos` position in """
    f = query('SELECT * FROM `sub_metadata` WHERE `key`=%s AND `value`=%s',
              (pos, uid))
    r = []
    for i in f.fetchall():
        r.append(get_sub_from_sid(i['sid']))
    return r


def is_password_valid(uid, password):
    """ Returns True if `password` matches the user's password """
    user = get_user_from_uid(uid)
    if user['crypto'] == 1:  # bcrypt
        thash = bcrypt.hashpw(password.encode('utf-8'),
                              user['password'].encode('utf-8'))
        if thash == user['password'].encode('utf-8'):
            return True
    return False


def update_user_password(uid, password):
    """ Changes a user's password """
    password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    if isinstance(password, bytes):
        password = password.decode('utf-8')

    uquery('UPDATE `user` SET `password`=%s WHERE `uid`=%s', (password, uid))
