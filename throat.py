#!/usr/bin/env python3
""" From here we start the app in debug mode. """
from gevent import monkey
monkey.patch_all()
from app import create_app, socketio  # noqa
app = create_app()

if __name__ == "__main__":
    socketio.run(app, debug=app.config.get('DEBUG'), host=app.config.get('HOST'))
