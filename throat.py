#!/usr/bin/env python3
""" From here we start the app in debug mode. """
from pathlib import Path
from gevent import monkey

monkey.patch_all()
import click  # noqa
from app import create_app, socketio  # noqa
from cli import commands  # noqa

app = create_app()


@click.group(invoke_without_command=True)
@click.pass_context
def run(ctx):
    if ctx.invoked_subcommand is None:
        extra_files = list(Path("./app/html").rglob("*.html"))
        extra_files.append("app/manifest.json")
        socketio.run(
            app,
            debug=app.config.get("DEBUG"),
            host=app.config.get("HOST"),
            extra_files=extra_files,
        )


for command in commands:
    run.add_command(command)


if __name__ == "__main__":
    run()
