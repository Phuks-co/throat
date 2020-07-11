from flask_socketio import SocketIO, join_room
from flask_login import current_user
from flask import request
from .models import rconn
import json
from wheezy.html.utils import escape_html


socketio = SocketIO()
#  The new stuff


@socketio.on('msg', namespace='/snt')
def chat_message(g):
    if g.get('msg') and current_user.is_authenticated:
        message = {'user': current_user.name, 'msg': escape_html(g.get('msg')[:250])}
        rconn.lpush('chathistory', json.dumps(message))
        rconn.ltrim('chathistory', 0, 20)
        socketio.emit('msg', message, namespace='/snt', room='chat')


@socketio.on('connect', namespace='/snt')
def handle_message():
    if current_user.get_id():
        join_room('user' + current_user.uid)
        socketio.emit('uinfo', {'taken': current_user.score,
                                'ntf': current_user.notifications},
                      namespace='/snt',
                      room='user' + current_user.uid)


@socketio.on('getchatbacklog', namespace='/snt')
def get_chat_backlog():
    msgs = rconn.lrange('chathistory', 0, 20)
    for m in msgs[::-1]:
        socketio.emit('msg', json.loads(m.decode()), namespace='/snt', room=request.sid)


@socketio.on('subscribe', namespace='/snt')
def handle_subscription(data):
    sub = data.get('target')
    if not sub:
        return
    if not str(sub).startswith('user'):
        join_room(sub)
