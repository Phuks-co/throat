from .recount import recount
from .admin import admin
from .default import default
from .migration import migration
from .translations import translations
commands = [
    migration,
    recount,
    admin,
    default,
    translations
]
