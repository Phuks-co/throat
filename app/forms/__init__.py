""" Uhh... Here we import stuff """
from .user import *  # noqa
from .sub import *  # noqa
from .admin import *  # noqa
from flask_wtf import FlaskForm


class CsrfTokenOnlyForm(FlaskForm):
    """This is here only for the csrf token."""

    pass
