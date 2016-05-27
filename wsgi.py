#!/usr/bin/python3
""" This is for openshift to run this app. """

import os

virtenv = os.environ['OPENSHIFT_PYTHON_DIR'] + '/virtenv/'
os.environ['PYTHON_EGG_CACHE'] = os.path.join(virtenv,
                                              'lib/python3.3/site-packages')
virtualenv = os.path.join(virtenv, 'bin/activate_this.py')
try:
    exec(compile(open(virtualenv).read(), virtualenv, 'exec'),
         dict(__file__=virtualenv))
    # execfile(virtualenv, dict(__file__=virtualenv))
except IOError:
    pass
#
# IMPORTANT: Put any additional includes below this line.  If placed above this
# line, it's possible required libraries won't be in your searchable path
#

from app import app as application
from app import db
with application.app_context():
    db.create_all()
