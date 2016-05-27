""" This is the config file. Pretty obvious, right? """
import os
_basedir = os.path.abspath(os.path.dirname(__file__))

# If we detect openshift, switch to production.
if os.getenv('OPENSHIFT_MYSQL_DB_HOST'):
    SQLALCHEMY_DATABASE_URI = "mysql://adminkpxkFRR:EIJhiwj18uVu@" \
                              "{0}:{1}/throat" \
                              .format(os.getenv('OPENSHIFT_MYSQL_DB_HOST'),
                                      os.getenv('OPENSHIFT_MYSQL_DB_PORT'))
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    DEBUG = True
    TESTING = False
else:
    SQLALCHEMY_DATABASE_URI = os.getenv('THROAT_DB') or \
                              'sqlite:////tmp/test.db'
    # Only for debugging and testing:
    SQLALCHEMY_TRACK_MODIFICATIONS = True
    DEBUG = True
    TESTING = True  # This makes all the captchas valid

SECRET_KEY = b'^[\x11"\\\x92H\x95-\xde\xc0\x07\xe3d^\xf6\xaa\xb4\xdf\xb5'

WTF_CSRF_ENABLED = True
WTF_CSRF_SECRET_KEY = SECRET_KEY

RECAPTCHA_PUBLIC_KEY = "6Lc3BSETAAAAALgiT5Yrp6o0fDfszklWMz4tGKFa"
RECAPTCHA_PRIVATE_KEY = "6Lc3BSETAAAAAB_3YE4sJY9UqJMEj_EZ0aYDrbuO"
