#!/usr/bin/env python3
""" From here we start the app in debug mode. """
from gevent import monkey
monkey.patch_all()
import click
from app import create_app, socketio  # noqa
from app.cli import commands

app = create_app()

@click.group(invoke_without_command=True)
@click.pass_context
def run(ctx):
    if ctx.invoked_subcommand is None:
        socketio.run(app, debug=app.config.get('DEBUG'), host=app.config.get('HOST'))


for command in commands:
    run.add_command(command)


if __name__ == "__main__":
    run()
