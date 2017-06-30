""" This is the config file. Pretty obvious, right? """
# Site title
LEMA = "Throat: Open discussion ;D"
COPY = "2016 Throat. All Rights Reserved."

DB_HOST = 'localhost'
DB_USER = 'root'
DB_PASSWD = ''
DB_NAME = 'phuks'

CACHE_TYPE = 'simple'
CACHE_REDIS_HOST = '127.0.0.1'
CACHE_REDIS_PORT = 6379
CACHE_REDIS_DB = 5
SOCKETIO_REDIS_URL = 'redis://127.0.0.1:6379/1'

SECRET_KEY = 'yS\x1c\x88\xd7\xb5\xb0\xdc\t:kO\r\xf0D{"Y\x1f\xbc^\xad'

WTF_CSRF_ENABLED = True
WTF_CSRF_SECRET_KEY = SECRET_KEY

# SENDGRID_API_KEY = "put it here"
SENDGRID_DEFAULT_FROM = "noreply@shitposting.space"

RECAPTCHA_PUBLIC_KEY = "6LeIxAcTAAAAAJcZVRqyHh71UMIEGNQ_MXjiZKhI"
RECAPTCHA_PRIVATE_KEY = "6LeIxAcTAAAAAGG-vFI1TnRWxMZNFuojJ4WifJWe"
THUMBNAILS = "./thumbs"
THUMBNAIL_HOST = "https://foo.bar"

# peewee
DATABASE = {
    'name': 'throat',
    'engine': 'MySQLDatabase',
    'user': 'root',
    'password': 'hunter2'
}

# SID of changelog sub
CHANGELOG_SUB = '9a79b49e-7bd3-4535-8ad6-ba11fc1d0ef5'

# Only for debugging and testing:
DEBUG = True
TESTING = True  # This makes all the captchas valid
