""" Sorting module. Here we store the classes that sort stuff. """


class BasicSorting(object):
    """ Base class for sorters. """
    entriesPerPage = 25

    def __init__(self, posts):
        """ posts is an array of SubPosts """
        # Normally here we'll sort em'.
        self.posts = posts

    def getPosts(self, page=1):
        return self.posts[(page-1) * self.entriesPerPage:
                          self.entriesPerPage * page]
