""" Uhh... Here we import stuff """
from .user import *
from .sub import *
from .admin import *


class DummyForm(FlaskForm):
    """ This is here only for the csrf token. """
    pass
