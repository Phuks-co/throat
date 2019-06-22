""" This is the config file. Pretty obvious, right? """
import os

# Site title
LEMA = "Throat: Open discussion ;D"
# Copyright notice, used in the footer
COPY = "2016 Throat. All Rights Reserved."

# Database connection information
DATABASE_URL = 'mysql://USER:PASSWD@localhost/throat'

# Method used to memoize stuff. Change to 'redis' if you use Redis
CACHE_TYPE = 'simple'
# Only used if CACHE_TYPE is 'redis'.
CACHE_REDIS_HOST = '127.0.0.1'
CACHE_REDIS_PORT = 6379
CACHE_REDIS_DB = 5

# The Redis that we use for SocketIO. This must be the same for all instances
SOCKETIO_REDIS_URL = 'redis://127.0.0.1:6379/1'

# Secret key used to encrypt session cookies. CHANGE THIS
SECRET_KEY = 'yS\x1c\x88\xd7\xb5\xb0\xdc\t:kO\r\xf0D{"Y\x1f\xbc^\xad'

# wtforms settings. Set to False to disable CSRF
WTF_CSRF_ENABLED = True
WTF_CSRF_SECRET_KEY = SECRET_KEY

# Sengrid API key, only used to send password recovery emails
SENDGRID_API_KEY = "put it here"
SENDGRID_DEFAULT_FROM = "noreply@shitposting.space"

# This is the path thumbnails will be stored on
THUMBNAILS = "./thumbs"
# This is the domain where the thumbnails are hosted on. Can be an absolute path too.
THUMBNAIL_HOST = "https://foo.bar/"
# THUMBNAIL_HOST = "/static/thumbnails"

# Same as above but for file storage (Used for user and sub file uploads)
STORAGE = "./stor"
STORAGE_HOST = "https://i.foo.bar/"

# SID of changelog sub (used to display last changelog entry on the sidebar)
# Leave empty to disable changelogs
CHANGELOG_SUB = ''

# Only for debugging and testing. Disable both in production
DEBUG = True
TESTING = True  # This makes all the captchas valid

# Max content-length accepted by the server
MAX_CONTENT_LENGTH = (1024 * 1024) * 10  # 10MB limit

# Prefix for subs. Must always start with /.
SUB_PREFIX = "/s"
