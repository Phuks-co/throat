# -*- coding: utf-8
""" Here is where all the good stuff happens """

import time
import socket
import datetime
from bs4 import BeautifulSoup
from flask import Flask, url_for, g, request
from flask_login import LoginManager, current_user
from flask_webpack import Webpack
from flask_babel import Babel, _
from wheezy.html.utils import escape_html

from .config import Config, config
from .forms import LoginForm, LogOutForm, CreateSubForm
from .models import db_init_app, rconn
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
from .socketio import socketio
from .misc import SiteAnon, engine, engine_init_app, re_amention, mail

# /!\ FOR DEBUGGING ONLY /!\
# from werkzeug.contrib.profiler import ProfilerMiddleware

webpack = Webpack()
babel = Babel()
login_manager = LoginManager()
login_manager.anonymous_user = SiteAnon
login_manager.login_view = 'auth.login'


def create_app(config=Config('config.yaml')):
    app = Flask(__name__)
    app.jinja_env.cache = {}
    app.config['THROAT_CONFIG'] = config
    app.config.update(config.get_flask_dict())
    app.config['WEBPACK_MANIFEST_PATH'] = 'manifest.json'

    if 'STORAGE_ALLOWED_EXTENSIONS' not in app.config:
        app.config['STORAGE_ALLOWED_EXTENSIONS'] = storage.allowed_extensions

    babel.init_app(app)
    jwt.init_app(app)
    webpack.init_app(app)
    socketio.init_app(app, message_queue=config.app.redis_url, cors_allowed_origins="*", async_mode="gevent")
    caching.cache.init_app(app)
    login_manager.init_app(app)
    rconn.init_app(app)
    db_init_app(app)
    re_amention.init_app(app)
    engine_init_app(app)
    if 'MAIL_SERVER' in app.config:
        mail.init_app(app)
    storage.storage_init_app(app)
    # app.wsgi_app = ProfilerMiddleware(app.wsgi_app)

    app.register_blueprint(home)
    app.register_blueprint(site)
    app.register_blueprint(sub, url_prefix=f'/{config.site.sub_prefix}')
    app.register_blueprint(user)
    app.register_blueprint(auth)
    app.register_blueprint(messages,  url_prefix='/messages')
    app.register_blueprint(subs)
    app.register_blueprint(wiki)
    app.register_blueprint(do)
    app.register_blueprint(api3, url_prefix='/api/v3')
    app.register_blueprint(errors)
    app.register_blueprint(admin, url_prefix='/admin')
    app.register_blueprint(mod, url_prefix='/mod')

    app.add_template_global(storage.file_url)
    app.add_template_global(storage.thumbnail_url)
    engine.global_vars.update({'current_user': current_user, 'request': request, 'config': config, 'conf': app.config,
                               'url_for': url_for, 'asset_url_for': webpack.asset_url_for, 'func': misc,
                               'form': forms, 'hostname': socket.gethostname(), 'datetime': datetime,
                               'e': escape_html, 'markdown': misc.our_markdown, '_': _, 'get_locale': get_locale,
                               'BeautifulSoup': BeautifulSoup, 'thumbnail_url': storage.thumbnail_url,
                               'file_url': storage.file_url})

    if config.app.development:
        import logging
        logging.basicConfig(level=logging.DEBUG)
        logging.getLogger("engineio.server").setLevel(logging.WARNING)
        logging.getLogger("socketio.server").setLevel(logging.WARNING)

    @app.before_request
    def before_request():
        """ Called before the request is processed. Used to time the request """
        g.start = time.time()

    @app.after_request
    def after_request(response):
        """ Called after the request is processed. Used to time the request """
        if not app.debug and not current_user.is_admin():
            return response  # We won't do this if we're in production mode
        if app.config['THROAT_CONFIG'].app.development:
            response.headers.add('Access-Control-Allow-Origin', '*')
            response.headers.add('Access-Control-Allow-Methods', 'GET,POST,PUT,PATCH,DELETE')
            response.headers.add('Access-Control-Allow-Headers', 'Content-Type,authorization')
        diff = time.time() - g.start
        diff = int(diff * 1000)
        if not hasattr(g, 'pqc'):
            g.pqc = 0
        if response.response and isinstance(response.response, list):
            etime = str(diff).encode()
            # TODO: Replace with globals sent to template
            response.response[0] = response.response[0] \
                .replace(b'__EXECUTION_TIME__', etime)
            response.response[0] = response.response[0] \
                .replace(b'__DB_QUERIES__', str(g.pqc).encode())
            response.headers["content-length"] = len(response.response[0])
        return response

    @app.context_processor
    def utility_processor():
        """ Here we set some useful stuff for templates """
        # TODO: Kill this huge mass of shit
        return {'loginform': LoginForm(), 'logoutform': LogOutForm(), 'csubform': CreateSubForm(),
                'markdown': misc.our_markdown, 'hostname': socket.gethostname(),
                'config': config, 'form': forms, 'datetime': datetime,
                'func': misc, 'time': time, 'conf': app.config, '_': _, 'locale': get_locale}

    return app


@babel.localeselector
def get_locale():
    if current_user.language:
        return current_user.language
    return request.accept_languages.best_match(config.app.languages, config.app.fallback_language)


@login_manager.user_loader
def load_user(user_id):
    """ This is used by flask_login to reload an user from a previously stored
    unique identifier. Required for the 'remember me' functionality. """
    return misc.load_user(user_id)
