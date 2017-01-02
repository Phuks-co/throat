#!/usr/bin/env python3
""" From here we start the app in debug mode. """
from app import app, socketio
if __name__ == "__main__":
    socketio.run(app)
