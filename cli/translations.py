import subprocess
from flask.cli import AppGroup

translations = AppGroup("translations", help="Manages translations")


@translations.command(help="Refreshes the translations potfile")
def genpot():
    subprocess.run(
        """pybabel extract \
    --msgid-bugs-address="polsaker@phuks.co" \
    --copyright-holder="Phuks LLC" \
    --project="Throat" \
    --version="1.0" \
    --mapping-file=babel.cfg \
    -k _l \
    -o app/translations/messages.pot .""",
        shell=True,
    )
    print("Done.")


@translations.command(
    name="compile", help="Compiles the translation .po files into .mo files"
)
def genmo():
    subprocess.run("pybabel compile -d app/translations", shell=True)
