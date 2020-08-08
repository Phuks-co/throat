from flask_socketio import SocketIO, join_room
from flask_login import current_user
from flask import request, current_app
from .models import rconn
import json
from wheezy.html.utils import escape_html
import logging


class SocketIOWithLogging(SocketIO):

    @property
    def __logger(self):
        return logging.getLogger(current_app.logger.name + ".socketio")

    def emit(self, event, *args, **kwargs):
        self.__logger.debug("EMIT %s %s %s", event, args[0], kwargs)
        super(SocketIOWithLogging, self).emit(event, *args, **kwargs)

    def on(self, message, namespace=None):
        def decorator(handler):
            def func(*args):
                self.__logger.debug("RECV %s %s", message, args[0] if args else '')
                handler(*args)
            return super(SocketIOWithLogging, self).on(message, namespace)(func)
        return decorator


socketio = SocketIOWithLogging()


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


@socketio.on('grabtitle', namespace='/snt')
def grab_title(data):
    token = data.get('token')
    if token is not None:
        join_room(token)
        result = rconn.get(token)
        if result is not None:
            socketio.emit('grabtitle', json.loads(result), namespace='/snt', room=token)


@socketio.on('subscribe', namespace='/snt')
def handle_subscription(data):
    sub = data.get('target')
    if not sub:
        return
    if not str(sub).startswith('user'):
        join_room(sub)
