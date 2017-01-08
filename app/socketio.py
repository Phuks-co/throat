from flask import session
from flask_socketio import SocketIO, join_room
from flask_login import current_user
from . import database as db
from . import misc

socketio = SocketIO()
#  The new stuff


def send_uinfo():
    socketio.emit('uinfo', {'loggedin': True, 'name': current_user.name,
                            'taken': current_user.get_post_score(),
                            'ntf': current_user.new_count(),
                            'given':
                            db.get_user_post_voting(current_user.uid)},
                  namespace='/alt',
                  room=session['usid'])


@socketio.on('connect', namespace='/alt')
def handle_uinfo():
    join_room(session['usid'])
    if current_user.is_authenticated:
        join_room('user' + current_user.uid)
        send_uinfo()
    else:
        socketio.emit('uinfo', {'loggedin': False}, namespace='/alt',
                      room=session['usid'])


@socketio.on('register', namespace='/alt')
def register_check(g):
    socketio.emit('rsettings', {'icode': misc.enableInviteCode()},
                  namespace='/alt')


# The old stuff


@socketio.on('connect', namespace='/snt')
def handle_message():
    if current_user.get_id():
        join_room('user' + current_user.uid)


@socketio.on('subscribe', namespace='/snt')
def handle_subscription(data):
    sub = data.get('target')
    if not sub:
        return
    if not str(sub).startswith('user'):
        join_room(sub)
