from flask_socketio import SocketIO, join_room
from flask_login import current_user
from flask import request
import redis
import config
import json

socketio = SocketIO()
redis = redis.from_url(config.SOCKETIO_REDIS_URL)
#  The new stuff


@socketio.on('msg', namespace='/snt')
def chat_message(g):
    if g.get('msg') and current_user.is_authenticated:
        message = {'user': current_user.name, 'msg': g.get('msg')}
        redis.lpush('chathistory', json.dumps(message))
        redis.ltrim('chathistory', 0, 20)
        socketio.emit('msg', message, namespace='/snt', room='chat')


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
        if sub == 'chat':
            msgs = redis.lrange('chathistory', 0, 20)
            for m in msgs[::-1]:
                socketio.emit('msg', json.loads(m.decode()), namespace='/snt', room=request.sid)
