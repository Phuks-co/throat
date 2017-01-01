from flask_socketio import SocketIO, join_room

socketio = SocketIO()


@socketio.on('connect')
def handle_message():
    pass  # We got a connection!


@socketio.on('subscribe', namespace='/snt')
def handle_subscription(data):
    sub = data['sub']
    join_room(sub)
