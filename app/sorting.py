""" Sorting module. Here we store the classes that sort stuff. """
from datetime import datetime
from math import log
from .caching import cache
import pyximport
pyximport.install()
from .sort import hot  # noqa


class BasicSorting(object):
    """ Base class for sorters. """
    entriesPerPage = 20

    def __init__(self, posts):
        """ posts is the query of SubPosts """
        # Normally here we'll sort em'.
        self.posts = list(posts)

    def getPosts(self, page=1):
        """ Gets the posts, sorted. """
        return self.posts[(page-1) * self.entriesPerPage:
                          self.entriesPerPage * page]


class VoteSorting(BasicSorting):
    """ Sorts by votes (/top) """
    def __init__(self, posts):
        super(VoteSorting, self).__init__(posts)
        self.posts.sort(key=lambda x: x['score'])
        self.posts.reverse()


class NewSorting(BasicSorting):
    """ Sorts by date (/new) """
    def __init__(self, posts):
        super(NewSorting, self).__init__(posts)
        self.posts.sort(key=lambda x: x['posted'].isoformat())
        self.posts.reverse()


class HotSorting(BasicSorting):
    """ Sorts by age and votes (/hot) """
    epoch = datetime(1970, 1, 1)

    def __init__(self, posts):
        super(HotSorting, self).__init__(posts)
        self.posts.sort(key=lambda x: hot.get_score(x['score'],
                                                    x['posted'].timestamp()),
                        reverse=True)

    def epoch_seconds(self, date):
        """ Returns seconds since the post was created """
        td = date - self.epoch
        return td.days * 86400 + td.seconds + (float(td.microseconds) /
                                               1000000)

    @cache.memoize(600)
    def get_score(self, post):
        """ Returns the /hot score for this post """
        s = post['score']
        order = log(max(abs(s), 1), 10)
        sign = 1 if s > 0 else -1 if s < 0 else 0
        seconds = self.epoch_seconds(post['posted']) - 1134028003
        return round(sign * order + seconds / 45000, 7)
