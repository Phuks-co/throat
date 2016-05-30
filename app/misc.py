""" Misc helper function and classes. """
from .models import db, SubMetadata


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

    def is_mod(self, sub):
        return isMod(sub, self.user)


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


def hasVoted(uid, post, up=True):
    """ Checks if the user up/downvoted the post. """
    vote = post.votes.filter_by(uid=uid).first()
    if vote:
        if vote.positive == up:
            return True
    else:
        return False


def getMetadata(obj, key, value=None):
    """ Gets metadata out of 'obj' (either a Sub, SubPost or User) """
    x = obj.properties.filter_by(key=key).first()
    if x and value is None:
        return x.value
    if x:
        x.value = value
    else:
        x = obj.__class__(obj, key, value)
        db.session.add(x)
    db.session.commit()


def isMod(sub, user):
    """ Returns True if 'user' is a mod of 'sub' """
    x = sub.properties.filter_by(key='mod').filter_by(value=user.uid).first()
    if x:
        return True  # user is mod
    else:
        return False
