""" This is the config file. Pretty obvious, right? """

# We're using a sqlite database for testing.
# In production we _should_ use mysql or something else
SQLALCHEMY_DATABASE_URI = 'sqlite:////tmp/test.db'
SECRET_KEY = "WTF!!"

# Only for debugging and testing:
SQLALCHEMY_TRACK_MODIFICATIONS = True
DEBUG = True
TESTING = True
