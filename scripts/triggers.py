#!/usr/bin/env python3
import __fix

from app.models import Badge
from app.badges import triggers
from app import create_app

# TODO: Move to a celery task?
app = create_app()
with app.app_context():
    for badge in Badge.select().where(Badge.trigger != None):
        triggers[badge.trigger](badge.bid)

