""" Sorting module. Here we store the classes that sort stuff. """


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
