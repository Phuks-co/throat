from flask import session
from flask_socketio import SocketIO, join_room
from flask_login import current_user
from . import database as db
from . import misc

socketio = SocketIO()
#  The new stuff


@socketio.on('msg', namespace='/snt')
def chat_message(g):
    if g.get('msg'):
        socketio.emit('msg', {'user': current_user.name, 'msg': g.get('msg')},
                      namespace='/snt', room='chat')


@socketio.on('connect', namespace='/snt')
def handle_message():
    if current_user.get_id():
        join_room('user' + current_user.uid)
        socketio.emit('uinfo', {'taken': current_user.get_post_score(),
                                'ntf': current_user.new_count()},
                      namespace='/snt',
                      room='user' + current_user.uid)


@socketio.on('subscribe', namespace='/snt')
def handle_subscription(data):
    sub = data.get('target')
    if not sub:
        return
    if not str(sub).startswith('user'):
        join_room(sub)
