from .recount import recount
from .admin import admin
from .default import default
from .migration import migration
from .route import route
from .translations import translations

commands = [migration, recount, route, admin, default, translations]
