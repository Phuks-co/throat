""" From here we start the app for a production environment. """
from gevent import monkey

# If the gunicorn worker is one of the gevent ones, it will have
# already done monkey patching, so use that to determine what kind of
# worker is running.

if monkey.is_module_patched("os"):
    # Monkey patch the Postgres driver.
    from psycogreen.gevent import patch_psycopg

    patch_psycopg()

else:
    # Prefer noisy failure to silent misbehavior, so do our own monkey
    # patching of gevent calls to raise errors.
    import app.misc
    import app.storage
    import app.tasks

    class GeventPatch:
        def sleep(self):
            raise RuntimeError(
                "Load balancer misconfiguration: gevent.sleep called from a sync worker"
            )

        def spawn(self, fn, *args):
            raise RuntimeError(
                "Load balancer misconfiguration: gevent.spawn called from a sync worker"
            )

    gevent_patch = GeventPatch()
    app.misc.gevent = gevent_patch
    app.storage.gevent = gevent_patch
    app.tasks.gevent = gevent_patch


from app import create_app  # noqa

app = create_app()
