#!/bin/bash
cd $(git rev-parse --show-toplevel)
git pull
pip install -r requirements.txt
npm install
npm run build
./throat.py translations compile
./throat.py migration apply
killall -HUP gunicorn
