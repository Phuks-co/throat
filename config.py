""" This is the config file. Pretty obvious, right? """

# We're using a sqlite database for testing.
# In production we _should_ use mysql or something else
SQLALCHEMY_DATABASE_URI = 'sqlite:////tmp/test.db'
SECRET_KEY = "WTF!!"

RECAPTCHA_PUBLIC_KEY = "6LeIxAcTAAAAAJcZVRqyHh71UMIEGNQ_MXjiZKhI"
RECAPTCHA_PRIVATE_KEY = "6LeIxAcTAAAAAGG-vFI1TnRWxMZNFuojJ4WifJWe"

# Only for debugging and testing:
SQLALCHEMY_TRACK_MODIFICATIONS = True
DEBUG = True
TESTING = True  # This makes all the captchas valid
