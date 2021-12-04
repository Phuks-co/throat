# Deploying Throat with `gunicorn`

For most instances we recommend having two `gunicorn` workers:

- One to handle websocket traffic:
```
gunicorn -w 1 throat_prod:app --worker-class geventwebsocket.gunicorn.workers.GeventWebSocketWorker --worker-connections 40 --bind ...
```

- And one for the regular HTTP requests:
```
gunicorn -w 1 throat_prod:app --worker-class gevent --worker-connections 40 --bind ...
```

Only a few routes require the async capabilities of `gevent`.  So you may also run `gunicorn`  sync workers, and
use `nginx` or a load balancer to direct the routes requiring async handling to the `geventwebsocket` or `gevent` workers:

```
gunicorn -w 4 throat_prod:app --bind ...
```

*Note: See the `gunicorn` documentation for suggestions on how to tweak the `-w` parameter (number of workers) for your needs.  The number of workers for the `geventwebsocket` worker must always be 1.*


# Deploying Throat with `docker`

The `Dockerfile` creates an image which can launch all three types of `gunicorn` workers, depending on which environment variables are set for `docker run`.

For example:

```
docker run --rm --env WORKER_TYPE=gevent --env WORKER_CONNECTIONS=40 throat    # To launch a gevent worker
docker run --rm --env WORKER_TYPE=socketio --env WORKER_CONNECTIONS=40 throat  # To launch a socketio worker
docker run --rm --env WORKER_TYPE=sync --env WORKER_COUNT=4 throat      # To launch 4 sync workers
```

The `Dockerfile` brings up `gunicorn` on port 5000.

# Load balancer configuration

Unless you just have one `gunicorn` process using a `geventwebsocket` worker and which is configured to handle SSL, you will need to put a load balancer or other web server in front of `gunicorn` or your docker containers. We recommend using `nginx` for this purpose.

If you use `nginx` or another web server or load balancer you must update the `trusted_proxy_count` setting in `config.yaml` or set the environment variable `SITE_TRUSTED_PROXY_COUNT` in order for the rate limiters to function correctly.

The following `nginx.conf` snippet directs HTTP traffic to a `gunicorn` process running on `someport`:

```
location / {
    include proxy_params;
    proxy_pass http://127.0.0.1:someport;
}
```
 
To make `nginx` properly serve the websocket requests you will need to add the following snippet to your
server block:

```
location /socket.io {
    include proxy_params;
    proxy_http_version 1.1;
    proxy_buffering off;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "Upgrade";
    proxy_pass http://127.0.0.1:some_port/socket.io;
}
```

You can use a `gunicorn` process with sync workers to serve most routes, except for `/socket.io` and a few others which require async capabilities.  The command `./throat.py route list` will produce a listing of all routes defined in Throat (except for static routes and `/socket.io`), showing whether `gevent` is required to serve them.

To redirect one or more routes to a different `gunicorn` process, add snippets such as the following to your `nginx.conf`:

```
location /login {
    include proxy_params;
    proxy_pass http://127.0.0.1:some_other_port;
}
```

Serving static files directly via `nginx` can relieve some load from the `gunicorn` workers:

```
location /static {
    alias /some/path/throat/app/static;
    expires max;
    access_log off;
    add_header "Access-Control-Allow-Origin"  *;
}
```

# Database connections

Database servers limit the number of connections, so you have to configure your `gunicorn` processes to use less than that limit, or you will see errors when your server is under load and a worker fails to acquire a database connection.

The two types of async workers, `gevent` and `geventwebsocket` benefit from database connection pooling, which can be configured externally to the application (PgBouncer is an example) or internally using the `database.engine` variable in `config.yaml`.
 
To configure database pooling using `database.engine`, see [the connection pooling documentation for Peewee](http://docs.peewee-orm.com/en/latest/peewee/playhouse.html#connection-pool).  You will need to use one of the pooled database classes in `database.engine`, for example:

```
database:
    ...
    engine: 'playhouse.pool.PooledPostgresqlDatabase'
    ...
```

You may wish to supply values in the `database` section of your `config.yaml` for `max_connections` and `stale_timeout`.  The sum total of `max_connections` for all your `gunicorn` workers should be less than your database's connection limit.

A `gunicorn` sync worker will need one database connection, unless you set the number of threads per worker to something other than 1 on the `gunicorn` command line, in which case it will need one connection per thread.

The `gevent` and `geventwebsocket` workers create a new green thread for each request.  Most requests require a database connection, and unless you put a stop to it a heavily loaded async server can start asking for more database connections than exist in the pool or on the database server.  The way to fix that is to include `--worker-connections 40` or whatever value you choose on the `gunicorn` command line.  You must choose a value which is less than or equal to `database.max_connections` if you are using database pooling.  If you do not give `gunicorn` a value for `--worker-connections`, it will default to 1000, which is likely to be more than the number of database connections available.

# Multiple configurations

The `Dockerfile` also supports storing multiple configurations in the `configs` directory.  You can specify a configuration to use by passing the `CONFIG_NAME` environment variable to `docker run`.  Multiple configurations may be useful if you maintain a test server in addition to your production server.  See [`start_all.sh`](start_all.sh) for details.
