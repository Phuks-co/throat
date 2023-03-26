""" Pages to be migrated to a wiki-like system """
from flask import Blueprint, request, redirect, url_for, jsonify
from ..misc import engine, logger, ensure_locale_loaded, get_locale
from ..caching import cache

bp = Blueprint("errors", __name__)


@bp.app_errorhandler(401)
def unauthorized(_):
    """401 Unauthorized"""
    return redirect(url_for("auth.login"))


@bp.app_errorhandler(403)
def forbidden_error(_):
    """403 Forbidden"""
    return render_error_template("errors/403.html"), 403


@bp.app_errorhandler(404)
def not_found(_):
    """404 Not found error"""
    if request.path.startswith("/api"):
        if request.path.startswith("/api/v3"):
            return jsonify(msg="Method not found or not implemented"), 404
        return jsonify(status="error", error="Method not found or not implemented"), 404
    return render_error_template("errors/404.html"), 404


@bp.app_errorhandler(417)
def teapot_error(_):
    """418 I'm a teapot"""
    return render_error_template("errors/417.html"), 418


@bp.app_errorhandler(429)
def too_many_requests_error(_):
    """429 Too many requests"""
    return render_error_template("errors/429.html"), 429


@bp.app_errorhandler(500)
def server_error(_):
    """500 Internal server error"""
    import traceback
    import sys

    typ, val, tb = sys.exc_info()
    logger.error('EXCEPTION: %s, "%s", %s', typ.__name__, val, traceback.format_tb(tb))
    if request.path.startswith("/api"):
        if request.path.startswith("/api/v3"):
            return jsonify(msg="Internal error"), 500
        return jsonify(status="error", error="Internal error"), 500

    return render_error_template("errors/500.html"), 500


def render_error_template(template):
    ensure_locale_loaded()
    lang = get_locale()
    daynight_cookie = request.cookies.get("dayNight")
    return _render_error_template(template, lang, daynight_cookie)


@cache.memoize(300)
def _render_error_template(template, *_):
    return engine.get_template(template).render({})
