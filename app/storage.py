""" Store and serve uploads and thumbnails. """
from flask import url_for
from flask_cloudy import Storage()
from .config import config


storage = Storage()


def make_url(local_url, name):
    if config.storage.provider == 'LOCAL' and not config.storage.server:
        return local_url + name
    else:
        obj = storage.get(name)
        if obj is None:
            return url_for('static', filename='file-not-found.png')
        else:
            return obj.url


def file_url(name):
    return make_url(config.storage.uploads.url, name)


def thumbnail_url(name):
    return make_url(config.storage.thumbnails.url, name)
