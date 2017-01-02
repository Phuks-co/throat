from flask_socketio import SocketIO, join_room
from flask_login import current_user

socketio = SocketIO()


@socketio.on('connect', namespace='/snt')
def handle_message():
    join_room('user' + current_user.uid)


@socketio.on('subscribe', namespace='/snt')
def handle_subscription(data):
    sub = str(data['target'])
    if not sub.startswith('user'):
        join_room(sub)
