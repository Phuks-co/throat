#throat

https://phuks.co/

A phoxy link and discussion aggregator with snek (python3)

##Dependencies:

 - MySQL/MariaDB or any compatible server.
 - Redis
 - Python >= 3.5 (3.7 not supported yet)
 - A recent node/npm

### On Ubuntu/Debian
 - apt-get install redis-server python3 python3-pip libmagic-dev mysql-server mysql-client libmysqlclient-dev libexiv2-dev libssl1.0-dev zlib1g-dev libbz2-dev libreadline-dev libsqlite3-dev libffi-dev libboost-python-dev

## Setup:

Jet the javascript dependencies and build the bundles with
 - $ npm install
 - $ npm run build

Install the Python requirements
 - $ pip3 install -r requirements.txt

Copy example.config.py and edit it

Set up the database
 - $ ./scripts/migrate.py

---

You can manage default subs by using 

 - $ ./scripts/defaults.py

To add/remove administrators use

 - $ ./scripts/admins.py
