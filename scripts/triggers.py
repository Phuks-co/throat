#!/usr/bin/env python3
import __fix

from flask_babel import lazy_gettext as _l
from app.models import UserMetadata, Badge
from app.badges import badges, triggers
from app import create_app


app = create_app()
with app.app_context():
    for badge in Badge.select().where(Badge.trigger != None):
        triggers[badge.trigger](badge.bid)

