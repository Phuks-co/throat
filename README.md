Note: Throat is developed and run on Python 3.6+. Previous versions are not supported

#throat

https://phuks.co/

A phoxy link and discussion aggregator with snek (python3)

##Dependencies:

Check `requirements.txt`

##Run local:

from ubuntu 16.04

 - $ apt-get update
 - $ apt-get install git python3-pip libssl-dev libffi-dev libpq-dev python3-dev libsqlite3-dev libexiv2-dev libboost-python-dev libmysqlclient-dev

Install the latest node and npm too.

clone and install

 - $ git clone <repo url>
 - $ cd throat
 - $ pip3 install -r requirements.txt
 - $ npm install
 - $ npm run build

run

 - $ ./wsgi.py

---

Note for future self: Ensure the mysql uses fucking utf8
Note from past self: Boo.
