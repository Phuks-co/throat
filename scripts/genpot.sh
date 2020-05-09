#!/bin/sh
pybabel extract \
    --msgid-bugs-address="polsaker@phuks.co" \
    --copyright-holder="Phuks LLC" \
    --project="Throat" \
    --version="1.0" \
    --mapping-file=babel.cfg \
    -k _l \
    -o app/translations/messages.pot .
