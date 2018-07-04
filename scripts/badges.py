#!/usr/bin/env python3

import __fix
from app import database as db
import datetime
from app.models import MiningLeaderboard, User, UserMetadata, Message
from app import socketio

tm = MiningLeaderboard.select().where(MiningLeaderboard.score > 1000000000)

for k in tm:
    try:
        us = User.get(User.name == k.username)
        # user exists
        try:
            um = UserMetadata.get((UserMetadata.uid == us.uid) & (UserMetadata.key == 'badge') & (UserMetadata.value == 'miner'))
        except UserMetadata.DoesNotExist:
            # doesn't have the badge
            um = UserMetadata(uid=us.uid, key='badge', value='miner')
            um.save()
            msg = Message(receivedby=us.uid, subject='Thank you!',
                          content='Thanks for donating so much CPU time to Phuks, we just gave you a nice little badge :)',
                          mtype=1, posted=datetime.datetime.utcnow())
            msg.save()
            mc = Message.select().where(Message.receivedby == us.uid) \
                .where(Message.mtype != 6).where(Message.read == None).count()
            socketio.emit('notification',
                          {'count': mc},
                          namespace='/snt',
                          room='user' + us.uid)
    except User.DoesNotExist:
        pass
