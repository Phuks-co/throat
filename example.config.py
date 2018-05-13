""" This is the config file. Pretty obvious, right? """
import os

# Site title
LEMA = "Throat: Open discussion ;D"
# Copyright notice, used in the footer
COPY = "2016 Throat. All Rights Reserved."

# XXX: LEGACY - FIX EVERYTHING AND REMOVE THIS BLOCK
DB_HOST = 'localhost'
DB_USER = os.getenv('DB_USER') or 'root'
DB_PASSWD = os.getenv('DB_PASSWD') or ''
DB_NAME = os.getenv('DB_NAME') or 'phuks'

# peewee
DATABASE_URL = 'mysql://{0}:{1}@localhost/{2}'.format(DB_USER, DB_PASSWD, DB_NAME)

# Method used to memoize stuff.
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

# Recaptcha credentials
RECAPTCHA_PUBLIC_KEY = "6LeIxAcTAAAAAJcZVRqyHh71UMIEGNQ_MXjiZKhI"
RECAPTCHA_PRIVATE_KEY = "6LeIxAcTAAAAAGG-vFI1TnRWxMZNFuojJ4WifJWe"

# This is the path thumbnails will be stored on
THUMBNAILS = "./thumbs"
# This is the domain where the thumbnails are hosted on. Can be an absolute path too.
THUMBNAIL_HOST = "https://foo.bar/"
# THUMBNAIL_HOST = "/static/thumbnails"

# Same as above but for file storage (Used for user and sub file uploads)
STORAGE = "./stor"
STORAGE_HOST = "https://i.foo.bar/"


# SID of changelog sub (used to display last changelog entry on the sidebar)
CHANGELOG_SUB = '9a79b49e-7bd3-4535-8ad6-ba11fc1d0ef5'

# Only for debugging and testing:
DEBUG = True
TESTING = True  # This makes all the captchas valid

# Address of the socketio server. If it's left empty socketio will attempt to connect
# to /socket.io.
WEBSOCKET_SERVER = '127.0.0.1:5000'

# Max content-length accepted by the server
MAX_CONTENT_LENGTH = (1024 * 1024) * 10  # 10MB limit

# Prefix for subs. Must always start with /.
SUB_PREFIX = "/s"
