# -*- coding: utf-8
""" Here is where all the good stuff happens """

import time
import socket
import datetime
from pathlib import Path
from bs4 import BeautifulSoup
from flask import Flask, url_for, g, request, get_flashed_messages
from flask_login import LoginManager, current_user
from flask_webpack import Webpack
from flask_babel import lazy_gettext as _l, _
from wheezy.html.utils import escape_html
from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.wrappers import BaseResponse

from .config import Config
from .forms import LoginForm, LogOutForm, CreateSubForm
from .models import db_init_app, rconn, User, SiteMetadata
from .auth import auth_provider, email_validation_is_required
from .views import do, subs as sub, api3, jwt
from .views.auth import bp as auth
from .views.home import bp as home
from .views.site import bp as site
from .views.user import bp as user
from .views.subs import bp as subs
from .views.wiki import bp as wiki
from .views.admin import bp as admin
from .views.mod import bp as mod
from .views.errors import bp as errors
from .views.messages import bp as messages

from . import misc, forms, caching, storage
from .notifications import notifications
from .socketio import socketio
from .misc import SiteAnon, engine, re_amention, mail, talisman, limiter
from .misc import logging_init_app, get_locale, babel

# /!\ FOR DEBUGGING ONLY /!\
# from werkzeug.middleware.profiler import ProfilerMiddleware

webpack = Webpack()
login_manager = LoginManager()
login_manager.anonymous_user = SiteAnon
login_manager.login_view = "auth.login"

# Allow translation of the messages shown by flask_login.
login_manager.login_message = _l("Please log in to access this page.")
login_manager.needs_refresh_message = _l("Please reauthenticate to access this page.")


def create_app(config=None):
    if config is None:
        config = Config("config.yaml", model=SiteMetadata, cache=caching.cache)
    app = Flask(__name__)
    app.jinja_env.cache = {}
    app.config["THROAT_CONFIG"] = config
    app.config.update(config.get_flask_dict())
    app.config["WEBPACK_MANIFEST_PATH"] = "manifest.json"

    if "STORAGE_ALLOWED_EXTENSIONS" not in app.config:
        app.config["STORAGE_ALLOWED_EXTENSIONS"] = storage.allowed_extensions

    # For flask-login, securely handle the "Remember me" cookie.
    app.config["REMEMBER_COOKIE_HTTPONLY"] = True
    app.config["REMEMBER_COOKIE_SECURE"] = not app.config["DEBUG"]

    csp = {
        "default-src": ["'self'"],
        "child-src": ["'self'"]
        + [f"https://{url}" for url in config.site.expando_sites],
        "img-src": ["'self'", "data:", "https:", "blob:"],
        "media-src": ["'self'", "https:"],
        "style-src": ["'self'", "'unsafe-inline'"],
        "connect-src": ["'self'"] + config.site.extra_connect_src,
    }

    if "server_name" in config.site.keys():
        csp["connect-src"] += [f"wss://{config.site.server_name}"]
        if not config.app.force_https:
            csp["connect-src"] += [f"ws://{config.site.server_name}"]

    talisman.init_app(
        app, content_security_policy=csp, force_https=config.app.force_https
    )

    babel.init_app(app)
    jwt.init_app(app)
    webpack.init_app(app)
    rconn.init_app(app)
    socketio.init_app(
        app,
        message_queue=config.app.redis_url,
        cors_allowed_origins="*",
        async_mode="gevent",
    )
    caching.cache.init_app(app)
    login_manager.init_app(app)
    db_init_app(app)
    re_amention.init_app(app)
    if "MAIL_SERVER" in app.config:
        mail.init_app(app)
    storage.storage_init_app(app)
    auth_provider.init_app(app)
    logging_init_app(app)
    limiter.init_app(app)
    notifications.init_app(app)

    # app.wsgi_app = ProfilerMiddleware(app.wsgi_app)

    app.register_blueprint(home)
    app.register_blueprint(site)
    app.register_blueprint(sub, url_prefix=f"/{config.site.sub_prefix}")
    app.register_blueprint(user)
    app.register_blueprint(auth)
    app.register_blueprint(messages, url_prefix="/messages")
    app.register_blueprint(subs)
    app.register_blueprint(wiki)
    app.register_blueprint(do)
    app.register_blueprint(api3, url_prefix="/api/v3")
    app.register_blueprint(errors)
    app.register_blueprint(admin, url_prefix="/admin")
    app.register_blueprint(mod, url_prefix="/mod")

    app.add_template_global(storage.file_url)
    app.add_template_global(storage.thumbnail_url)

    # load the logo
    if not Path(config.site.logo).is_absolute():
        # If it's not an absolute path we assume it's relative to the root project path
        logo_fp = open(f"{Path(__file__).parent.parent.absolute()}/{config.site.logo}")
    else:
        logo_fp = open(config.site.logo)
    THROAT_LOGO = logo_fp.read()
    logo_fp.close()
    engine.global_vars.update(
        {
            "current_user": current_user,
            "request": request,
            "config": config,
            "conf": app.config,
            "url_for": url_for,
            "asset_url_for": webpack.asset_url_for,
            "func": misc,
            "form": forms,
            "hostname": socket.gethostname(),
            "datetime": datetime,
            "e": escape_html,
            "markdown": misc.our_markdown,
            "_": _,
            "get_locale": get_locale,
            "BeautifulSoup": BeautifulSoup,
            "thumbnail_url": storage.thumbnail_url,
            "file_url": storage.file_url,
            "get_flashed_messages": get_flashed_messages,
            "email_validation_is_required": email_validation_is_required,
            "THROAT_LOGO": THROAT_LOGO,
        }
    )

    if config.site.trusted_proxy_count != 0:
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=config.site.trusted_proxy_count)

    # Don't let Werkzeug make the Location header into a full URL, because relative
    # paths are legal in Location and because Werkzeug gets it wrong if the app is
    # behind a load balancer which terminates SSL.
    BaseResponse.autocorrect_location_header = False

    @app.before_request
    def before_request():
        """ Called before the request is processed. Used to time the request """
        g.start = time.time()

    @app.after_request
    def after_request(response):
        """ Called after the request is processed. Used to time the request """
        if hasattr(g, "start"):
            diff = int((time.time() - float(g.start)) * 1000)
        else:
            diff = "unknown"
        if not hasattr(g, "pqc"):
            g.pqc = 0
        app.logger.info("%s (%s ms, %s queries)", response.status, diff, g.pqc)
        if not app.debug:
            return response  # We won't do this if we're in production mode
        if app.config["THROAT_CONFIG"].app.development:
            response.headers.add("Access-Control-Allow-Origin", "*")
            response.headers.add(
                "Access-Control-Allow-Methods", "GET,POST,PUT,PATCH,DELETE"
            )
            response.headers.add(
                "Access-Control-Allow-Headers", "Content-Type,authorization"
            )
        if not hasattr(g, "start"):
            return response
        if response.response and isinstance(response.response, list):
            etime = str(diff).encode()
            # TODO: Replace with globals sent to template
            response.response[0] = response.response[0].replace(
                b"__EXECUTION_TIME__", etime
            )
            response.response[0] = response.response[0].replace(
                b"__DB_QUERIES__", str(g.pqc).encode()
            )
            response.headers["content-length"] = len(response.response[0])
        return response

    @app.context_processor
    def utility_processor():
        """ Here we set some useful stuff for templates """
        # TODO: Kill this huge mass of shit
        return {
            "loginform": LoginForm(),
            "logoutform": LogOutForm(),
            "csubform": CreateSubForm(),
            "markdown": misc.our_markdown,
            "hostname": socket.gethostname(),
            "config": config,
            "form": forms,
            "datetime": datetime,
            "func": misc,
            "time": time,
            "conf": app.config,
            "_": _,
            "locale": get_locale,
            "THROAT_LOGO": THROAT_LOGO,
        }

    return app


@login_manager.user_loader
def load_user(user_id):
    """This is used by flask_login to reload an user from a previously stored
    unique identifier. Required for the 'remember me' functionality.
    The unique identifier is the user_id and their number of password resets."""
    splits = user_id.split("$")
    user = User.get(User.uid == splits[0])
    resets = 0 if len(splits) == 1 else int(splits[1])
    if resets == user.resets:
        return misc.load_user(user.uid)
    else:
        return None
