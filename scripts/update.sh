#!/bin/bash
cd $(git rev-parse --show-toplevel)
git pull
pip install -r requirements.txt
npm install
npm run build
./scripts/genmo.sh
./scripts/migrate.py
killall -HUP gunicorn
