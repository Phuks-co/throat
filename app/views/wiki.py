""" Pages to be migrated to a wiki-like system """
from flask import Blueprint, render_template
from flask_babel import lazy_gettext as _l
from ..misc import engine

bp = Blueprint('wiki', __name__)


@bp.route("/welcome")
def welcome():
    """ Welcome page for new users """
    return render_template('welcome.html')


@bp.route("/canary")
def canary():
    """ Warrent canary """
    return render_template('canary.html')


@bp.route("/donate")
def donate():
    """ Donation page """
    return render_template('donate.html')


try:
    th_license = open('LICENSE', 'r').read()
except FileNotFoundError:
    th_license = _l('License file was deleted :(')


@bp.route("/license")
def license():
    """ View API help page """
    return engine.get_template('site/license.html').render({'license': th_license})


@bp.route("/api")
def view_api():
    """ View API help page """
    return render_template('api.html')


@bp.route("/tos")
def tos():
    """ Shows the site's TOS. """
    return render_template('tos.html')


@bp.route("/privacy")
def privacy():
    """ Shows the site's privacy policy. """
    return render_template('privacy.html')
