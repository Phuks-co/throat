#!/bin/bash
# Launch Throat for production or development inside a docker
# container.
#
# Control what is launched using environment variables:
#
# CONFIG_NAME: If this is set, use config files from ./config/$CONFIG_NAME
#          instead of the config in the project root directory.
#
# WORKER_TYPE: One of:
#              'local' (to launch the built-in flask server),
#              'gevent' (to launch gunicorn with a gevent worker),
#              'socketio' (to launch gunicorn with a geventwebsocket
#                          worker)
#              'sync' (to launch gunicorn with sync workers)
#
# WORKER_CONNECTIONS: Limit the number of worker connections gunicorn
#                     will accept for gevent and geventwebsocket workers.
# WORKER_COUNT: Set the number of sync workers to create.
# THREAD_COUNT: Set the number of threads used per sync worker.

if [[ -n $CONFIG_NAME ]]; then
    rm -rf config.yaml
    cp configs/${CONFIG_NAME}/* ./
fi

# Set a limit on the number of simultaneous clients for the gevent and
# socketio workers.  The gunicorn default is 1000.
if [[ -n $WORKER_CONNECTIONS ]]; then
    CONNECTIONS_OPTION="--worker-connections $WORKER_CONNECTIONS"
fi

if [[ $WORKER_TYPE == "local" ]]; then
    python3 ./throat.py

elif [[ $WORKER_TYPE == "sync" ]]; then
    # Start the sync worker server
    if [[ -z $WORKER_COUNT ]]; then
	# Number of processes for gunicorn to use.
	WORKER_COUNT=2
    fi

    # Setting this to >1 changes the gunicorn worker type from sync to gthread.
    # Number of database connections needed will be $WORKER_COUNT * $THREAD_COUNT.
    if [[ -z $THREAD_COUNT ]]; then
	THREAD_COUNT=1
    fi

    gunicorn -w $WORKER_COUNT --threads $THREAD_COUNT --worker-tmp-dir /dev/shm throat_prod:app \
	     --bind 0.0.0.0:5000

elif [[ $WORKER_TYPE == "socketio" ]]; then
    # Start the socketio listener
    gunicorn -w 1 --worker-tmp-dir /dev/shm --keep-alive 65 $CONNECTIONS_OPTION throat_prod:app \
	     --worker-class geventwebsocket.gunicorn.workers.GeventWebSocketWorker --bind 0.0.0.0:5000

elif [[ $WORKER_TYPE == "gevent" ]]; then
    # Start the gevent worker process
    gunicorn -w 1 --worker-tmp-dir /dev/shm --keep-alive 65 $CONNECTIONS_OPTION throat_prod:app \
	     --worker-class gevent --bind 0.0.0.0:5000
else
    echo "Unknown or unset WORKER_TYPE" 1>&2
    exit 1
fi
