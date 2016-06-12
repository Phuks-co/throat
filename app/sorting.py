""" Sorting module. Here we store the classes that sort stuff. """
from datetime import datetime, timedelta
from math import log


class BasicSorting(object):
    """ Base class for sorters. """
    entriesPerPage = 25

    def __init__(self, posts):
        """ posts is the query of SubPosts """
        # Normally here we'll sort em'.
        self.posts = posts.all()

    def getPosts(self, page=1):
        return self.posts[(page-1) * self.entriesPerPage:
                          self.entriesPerPage * page]


class VoteSorting(BasicSorting):
    def __init__(self, posts):
        super(VoteSorting, self).__init__(posts)
        self.posts.sort(key=lambda x: x.voteCount)
        self.posts.reverse()


class HotSorting(BasicSorting):
    epoch = datetime(1970, 1, 1)

    def __init__(self, posts):
        super(HotSorting, self).__init__(posts)

    def epoch_seconds(self, date):
        td = date - self.epoch
        return td.days * 86400 + td.seconds + (float(td.microseconds) /
                                               1000000)

    def get_score(self, post):
        s = post.voteCount
        order = log(max(abs(s), 1), 10)
        sign = 1 if s > 0 else -1 if s < 0 else 0
        seconds = self.epoch_seconds(post.posted) - 1134028003
        return round(sign * order + seconds / 45000, 7)
