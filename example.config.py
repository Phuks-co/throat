""" This is the config file. Pretty obvious, right? """
import os
_basedir = os.path.abspath(os.path.dirname(__file__))

# Site title
LEMA = "Throat: Open discussion ;D"
COPY = "2016 Throat. All Rights Reserved."
# We're using a sqlite database for testing.
# In production we _should_ use mysql or something else
SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL') or 'sqlite:////tmp/test.db'
CACHE_TYPE = 'simple'
CACHE_REDIS_HOST = '127.0.0.1'
CACHE_REDIS_PORT = 6379
CACHE_REDIS_DB = 5

SECRET_KEY = os.getenv('THROAT_SECRET') or \
             'yS\x1c\x88\xd7\xb5\xb0\xdc\t:kO\r\xf0D{"Y\x1f\xbc^\xad'

WTF_CSRF_ENABLED = True
WTF_CSRF_SECRET_KEY = SECRET_KEY

# SENDGRID_API_KEY = "put it here"
SENDGRID_DEFAULT_FROM = "noreply@shitposting.space"

RECAPTCHA_PUBLIC_KEY = "6LeIxAcTAAAAAJcZVRqyHh71UMIEGNQ_MXjiZKhI"
RECAPTCHA_PRIVATE_KEY = "6LeIxAcTAAAAAGG-vFI1TnRWxMZNFuojJ4WifJWe"
THUMBNAILS = "./thumbs"
THUMBNAIL_HOST = "https://foo.bar"

# Only for debugging and testing:
SQLALCHEMY_TRACK_MODIFICATIONS = True
DEBUG = True
TESTING = True  # This makes all the captchas valid
