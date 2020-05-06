# Web

https://cekni.to/

A link and discussion aggregator with snek (python3)

## Dependencies:

 - A database server, MySQL, MariaDB and Postres have been tested. Sqlite should work for messing locally
 - Redis
 - Python >= 3.5
 - A recent node/npm
 - libmagic and libexiv2

## Setup:

We recommend using a virtualenv or Pyenv

1. Install Python dependencies with `pip install -r requirements.txt`
2. Install Node dependencies with `npm install`
3. Build the bundles with `npm run build`
4. Copy `example.config.yml` to `config.yml` and edit it
5. Set up the database by executing `./scripts/migrate.py`

