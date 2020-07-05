""" Store and serve uploads and thumbnails. """
from flask_cloudy import Storage
from .config import config


storage = Storage()
