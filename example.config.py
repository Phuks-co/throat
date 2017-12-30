""" This is the config file. Pretty obvious, right? """
import os
# Site title
LEMA = "Throat: Open discussion ;D"
COPY = "2016 Throat. All Rights Reserved."

DB_HOST = 'localhost'
DB_USER = os.getenv('DB_USER') or 'root'
DB_PASSWD = os.getenv('DB_PASSWD') or ''
DB_NAME = os.getenv('DB_NAME') or 'phuks'

# Method used to memoize stuff.
CACHE_TYPE = 'simple'
# Only used if CACHE_TYPE is 'redis'.
CACHE_REDIS_HOST = '127.0.0.1'
CACHE_REDIS_PORT = 6379
CACHE_REDIS_DB = 5

# The Redis that we use for SocketIO. This must be the same for all instances
SOCKETIO_REDIS_URL = 'redis://127.0.0.1:6379/1'

SECRET_KEY = 'yS\x1c\x88\xd7\xb5\xb0\xdc\t:kO\r\xf0D{"Y\x1f\xbc^\xad'

WTF_CSRF_ENABLED = True
WTF_CSRF_SECRET_KEY = SECRET_KEY

SENDGRID_API_KEY = "put it here"
SENDGRID_DEFAULT_FROM = "noreply@shitposting.space"

RECAPTCHA_PUBLIC_KEY = "6LeIxAcTAAAAAJcZVRqyHh71UMIEGNQ_MXjiZKhI"
RECAPTCHA_PRIVATE_KEY = "6LeIxAcTAAAAAGG-vFI1TnRWxMZNFuojJ4WifJWe"

THUMBNAILS = "./thumbs"
THUMBNAIL_HOST = "https://foo.bar/"

STORAGE = "./stor"
STORAGE_HOST = "https://i.foo.bar/"

# peewee
DATABASE = {
    'name': DB_NAME,
    'engine': 'MySQLDatabase',
    'user': DB_USER,
    'password': DB_PASSWD,
    'host': DB_HOST
}

# SID of changelog sub
CHANGELOG_SUB = '9a79b49e-7bd3-4535-8ad6-ba11fc1d0ef5'

# Only for debugging and testing:
DEBUG = True
TESTING = True  # This makes all the captchas valid

WEBSOCKET_SERVER = '127.0.0.1:5000'


MAX_CONTENT_LENGTH = (1024 * 1024) * 10  # 10MB limit
