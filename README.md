# Web

https://cekni.to/

A link and discussion aggregator with snek (python3)

## Dependencies:

 - A database server, MySQL, MariaDB and Postgres have been tested. Sqlite should work for messing locally
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
6. Compile the translation files with `./scripts/genmo.sh`

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

## Database Configuration

The default hot sort function is simple for speed, but it does not prioritize new posts over old ones as much as some people prefer.  If you define a function named `hot` in SQL in your database, you can use that instead of the default by setting `custom_hot_sort` to `True` in your `config.yaml`.  The function needs to take two arguments, a post's current score and the date it was posted.  To allow the database to cache the results, the function should only depend on the values of its arguments and should be marked `immutable`.

In addition to defining the function, you should also create an index on it to speed up the hot sort query.  Once that is done, custom functions will be faster than the default hot sort.  To implement Reddit's version of hot sort in Postgres, add the following SQL statements to your database using `psql`:

```
create or replace function hot(score integer, date double precision) returns numeric as $$
  select round(cast(log(greatest(abs($1), 1)) * sign($1) + ($2 - 1134028003) / 45000.0 as numeric), 7)
$$ language sql immutable;

create index on sub_post (hot(score, (EXTRACT(EPOCH FROM sub_post.posted))));
```

Other databases may require variations in the handling of the date. Custom hot sorts are not supported for Sqlite.

## Docker Deployments

### Gunicorn
```
CMD [ "gunicorn", \
      "-w", "4", \
      "-k", "geventwebsocket.gunicorn.workers.GeventWebSocketWorker", \
      "-b", "0.0.0.0:5000", \
      "throat:app" ]
```

## Authenticating with a Keycloak server

Optionally, user authentication can be done using a Keycloak server.
You will need to create a realm for the users on the server, as well
as Keycloak clients with appropriate permissions.  See
`doc/keycloak.org` for instructions.

## Deploying to AWS

You can check out the [CDK Definition of Infrastructure](https://gitlab.com/feminist-conspiracy/infrastructure) maintained by Ovarit 

## Tests

### Python tests

1. Python, redis, libmagic and gobject are required, but node and postgres are not.
2. Install dependencies with `pip install -r requirements.txt`
3. Install the test dependencies with `pip install -r requirements-test.txt`
4. Run the tests with `python -m pytest`
5. The tests are not affected by your configuration in `config.yaml`.
If you wish to run the tests against production database or
authentication servers (instead of the defaults, which are sqlite and
local authentication), you may put configuration settings in
`test_config.yaml` and run the tests with
`TEST_CONFIG=test_config.yaml python -m pytest`

## Chat

If you have any questions, you can reach us on [Discord](https://discord.gg/Z59XKVB)

---

You can manage default subs by using 

 - $ ./scripts/defaults.py

To add/remove administrators use

 - $ ./scripts/admins.py
