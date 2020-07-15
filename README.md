# Throat

https://phuks.co/

A phoxy link and discussion aggregator with snek (python3)

## Dependencies:

 - A database server, MySQL, MariaDB and Postres have been tested. Sqlite should work for messing locally
 - Redis
 - Python >= 3.7
 - A recent node/npm
 - libmagic and gobject

## Setup:

We recommend using a virtualenv or Pyenv

1. Install Python dependencies with `pip install -r requirements.txt`
2. Install Node dependencies with `npm install`
3. Build the bundles with `npm run build`
4. Copy `example.config.yml` to `config.yml` and edit it
5. Set up the database by executing `./scripts/migrate.py`

And you're done! You can run a test server by executing `./throat.py`. For production instances we recommend setting up `gunicorn`

## Develop on Docker
If you prefer to develop on docker
 - The provided Docker resources only support Postgres
 - You still must copy `example.config.yaml` to `config.yaml` and make any changes you want
 - In addition, configs are overridden by environment variables set in docker-compose.yml
   which reference the redis and postgres services created by docker-compose.

`make up` will bring the containerized site up and mount your current working directory
inside the container for dev. It also runs the migrations on start-up. `make down` will spin down the containerized services.

To add an admin user to a running docker-compose application:
`docker exec throat_throat_1 python3 scripts/admins.py --add {{username}}`

If Wheezy templates are not automatically reloading in docker between changes, try `docker restart throat_throat_1`.

## Docker Deployments

### Gunicorn
```
CMD [ "gunicorn", \
      "-w", "4", \
      "-k", "geventwebsocket.gunicorn.workers.GeventWebSocketWorker", \
      "-b", "0.0.0.0:5000", \
      "throat:app" ]
```

## Tests

### Python tests

1. Python, redis, libmagic and gobject are required, but node and postgres are not.
2. Install dependencies with `pip install -r requirements.txt`
3. Install the test dependencies with `pip install -r requirements-test.txt`
4. Run the tests with `python -m pytest`

## Chat

If you have any questions, you can reach us on #throat:phuks.co on [Matrix](https://chat.phoxy.win/#/login)

---

You can manage default subs by using 

 - $ ./scripts/defaults.py

To add/remove administrators use

 - $ ./scripts/admins.py
