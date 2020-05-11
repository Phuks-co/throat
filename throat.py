#!/usr/bin/env python3
""" From here we start the app in debug mode. """
import eventlet
eventlet.monkey_patch()
from app import create_app, socketio  # noqa
app = create_app()

if __name__ == "__main__":
    socketio.run(app, debug=True)
