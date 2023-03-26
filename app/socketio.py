from flask_socketio import SocketIO, join_room
from flask_login import current_user
from flask_jwt_extended import decode_token
from flask import request
from .models import rconn
from . import misc
import gevent
from gevent import monkey
import json
import random
import re
from wheezy.html.utils import escape_html
import logging
import time
from engineio.payload import Payload

Payload.max_decode_packets = 50


# Time in seconds for the expiration of the Redis keys used to decide
# which instance should do the socketio.emit for messages received via
# Redis subscription.  This should be somewhere in between the longest
# time the gevent loop might get blocked and the acceptable time for
# messages to not get delivered if the instance that was doing the
# emitting goes down.
NAME_KEY_KEEPALIVE = 1


class SocketIOWithLogging(SocketIO):
    def init_app(self, app, **kwargs):
        super(SocketIOWithLogging, self).init_app(app, **kwargs)
        self.__logger = logging.getLogger(app.logger.name + ".socketio")
        if monkey.is_module_patched("os"):
            self.instance_name_prefix = "throat-socketio-instance-name-"
            self.instance_name = self.instance_name_prefix + "".join(
                [chr(random.randrange(0, 26) + ord("a")) for i in range(6)]
            )
            gevent.spawn(self.refresh_name_key)
            gevent.spawn(self.emit_messages)

    def emit(self, event, *args, **kwargs):
        self.__logger.debug("EMIT %s %s %s", event, args[0], kwargs)
        if "room" in kwargs:
            rconn.publish(
                kwargs["namespace"] + ":" + event + ":" + str(kwargs["room"]),
                json.dumps(args[0]),
            )
        super(SocketIOWithLogging, self).emit(event, *args, **kwargs)

    def on(self, message, namespace=None):
        def decorator(handler):
            def func(*args):
                self.__logger.debug("RECV %s %s", message, args[0] if args else "")
                handler(*args)

            return super(SocketIOWithLogging, self).on(message, namespace)(func)

        return decorator

    def refresh_name_key(self):
        """Keep a key set to expire in a few seconds alive on Redis."""
        while True:
            rconn.setex(
                name=self.instance_name,
                value="true",
                time=NAME_KEY_KEEPALIVE,
            )
            gevent.sleep(NAME_KEY_KEEPALIVE * 0.9)

    def emitting_instance(self):
        """Return True if this is the first instance in alphabetical order by
        instance name."""
        keys = rconn.keys(self.instance_name_prefix + "*")
        names = sorted([k.decode("utf-8") for k in keys])
        return len(names) == 0 or names[0] == self.instance_name

    def emit_messages(self):
        """Emit SocketIO events for messages from Redis."""
        pubsub = rconn.pubsub(ignore_subscribe_messages=True)
        pubsub.psubscribe("/send:*")
        for message in pubsub.listen():
            if self.emitting_instance():
                self.__logger.debug("PSUB %s", message)
                if message["type"] == "pmessage":
                    match = re.match(
                        r"/send:(.+?):(.+)", message["channel"].decode("utf-8")
                    )
                    if match:
                        try:
                            data = json.loads(message["data"])
                            self.emit(match[1], data, room=match[2], namespace="/snt")
                        except json.JSONDecodeError:
                            self.__logger.error(
                                "Failed to decode message on channel %s: %s",
                                message["channel"],
                                message["data"],
                            )


socketio = SocketIOWithLogging()


@socketio.on("msg", namespace="/snt")
def chat_message(g):
    if g.get("msg") and current_user.is_authenticated:
        message = {
            "time": time.time(),
            "user": current_user.name,
            "msg": escape_html(g.get("msg")[:250]),
        }
        rconn.lpush("chathistory", json.dumps(message))
        rconn.ltrim("chathistory", 0, 20)
        socketio.emit("msg", message, namespace="/snt", room="chat")


@socketio.on("connect", namespace="/snt")
def handle_message():
    if current_user.get_id():
        join_room("user" + current_user.uid)
        socketio.emit(
            "uinfo",
            {
                "taken": current_user.score,
                "ntf": current_user.notifications,
                "mod_ntf": current_user.mod_notifications(),
            },
            namespace="/snt",
            room="user" + current_user.uid,
        )


@socketio.on("getchatbacklog", namespace="/snt")
def get_chat_backlog():
    msgs = rconn.lrange("chathistory", 0, 20)
    for m in msgs[::-1]:
        socketio.emit("msg", json.loads(m.decode()), namespace="/snt", room=request.sid)


@socketio.on("deferred", namespace="/snt")
def handle_deferred(data):
    """Subscribe for notification of when the work associated with a
    target token (some unique string) is done.  The do-er of the work
    may have already finished and placed the result in Redis."""
    target = data.get("target")
    if target:
        target = str(target)
        join_room(target)
        result = rconn.get(target)
        if result is not None:
            result = json.loads(result)
            socketio.emit(
                result["event"], result["value"], namespace="/snt", room=target
            )


def send_deferred_event(event, token, data, expiration=30):
    """Both send an event, and stash the event and its data in Redis so it
    can be sent to any tardy subscribers."""
    rconn.setex(
        name=token, time=expiration, value=json.dumps({"event": event, "value": data})
    )
    socketio.emit(event, data, namespace="/snt", room=token)


@socketio.on("subscribe", namespace="/snt")
def handle_subscription(data):
    sub = data.get("target")
    if not sub:
        return
    if not str(sub).startswith("user"):
        join_room(sub)


@socketio.on("token-login", namespace="/snt")
def token_login(data):
    tokendata = decode_token(data["jwt"])

    join_room("user" + tokendata["identity"])

    socketio.emit(
        "notification",
        {"count": misc.get_notification_count(tokendata["identity"])},
        namespace="/snt",
        room="user" + tokendata["identity"],
    )
