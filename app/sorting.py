""" Sorting module. Here we store the classes that sort stuff. """


class BasicSorting(object):
    """ Base class for sorters. """
    entriesPerPage = 20

    def __init__(self, posts):
        """ posts is the query of SubPosts """
        # Normally here we'll sort em'.
        self.posts = list(posts)

    def getPosts(self, page=1):
        """ Gets the posts, sorted. """
        return self.posts[(page - 1) * self.entriesPerPage:
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
