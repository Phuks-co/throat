""" Pages to be migrated to a wiki-like system """
from flask import Blueprint, request, redirect, url_for, jsonify
from ..misc import engine
from ..forms import LoginForm

bp = Blueprint('errors', __name__)


@bp.app_errorhandler(401)
def unauthorized(error):
    """ 401 Unauthorized """
    return redirect(url_for('auth.login'))


@bp.app_errorhandler(403)
def forbidden_error(error):
    """ 403 Forbidden """
    return engine.get_template('errors/403.html').render({'loginform': LoginForm()}), 403


@bp.app_errorhandler(404)
def not_found(error):
    """ 404 Not found error """
    if request.path.startswith('/api'):
        if request.path.startswith('/api/v3'):
            return jsonify(msg="Method not found or not implemented"), 404
        return jsonify(status='error', error='Method not found or not implemented'), 404
    return engine.get_template('errors/404.html').render({}), 404


@bp.app_errorhandler(417)
def forbidden_error(error):
    """ 418 I'm a teapot """
    return engine.get_template('errors/417.html').render({}), 418


@bp.app_errorhandler(500)
def server_error(error):
    """ 500 Internal server error """
    if request.path.startswith('/api'):
        if request.path.startswith('/api/v3'):
            return jsonify(msg="Internal error"), 500
        return jsonify(status='error', error='Internal error'), 500

    return engine.get_template('errors/500.html').render({}), 500
