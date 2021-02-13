# Deploying Throat with gunicorn

For most instances we recommend having two gunicorn workers:
 - One for the regular HTTP requests:
```
gunicorn -w 2 throat:app --worker-class gevent --bind ...
```
 - And one to handle websocket traffic:
```
gunicorn -w 1 throat:app --worker-class geventwebsocket.gunicorn.workers.GeventWebSocketWorker --bind ...
```

*Note: The number of workers (`-w N`) can be tweaked for the HTTP worker according to your needs,
but it must **always**be one for the websocket worker.*

---
You will need to put a load balancer in  front of gunicorn. We recommend using Nginx for this purpose.

```
location / {
    include proxy_params;
    proxy_pass http://127.0.0.1:someport;
}
```
*Note: if you use Nginx you must update the `trusted_proxy_count` setting in the config file in order for the
rate limiters to function correctly*
 
To make Nginx properly serve the websocket requests you will need to add the following snippet to your
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

It is also recommended to serve static files directly via nginx to relieve some load from the gunicorn workers:

```
location /static {
    alias /some/path/throat/app/static;
    expires max;
    access_log off;
    add_header "Access-Control-Allow-Origin"  *;
}
```