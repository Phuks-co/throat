#!/usr/bin/env python3
""" From here we start the app in debug mode. """
import eventlet
eventlet.monkey_patch()

from app import app, socketio  # noqa
if __name__ == "__main__":
    socketio.run(app, debug=True)
