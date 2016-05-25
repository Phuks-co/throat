""" Misc helper function and classes. """


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
