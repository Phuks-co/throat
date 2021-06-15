from flask.cli import AppGroup, current_app

route = AppGroup("route", help="Get information on routes")


@route.command(name="list", help="List routes")
def list_routes():
    """List routes."""
    print(f"{'Rule':80}{'Endpoint':35}{'Methods':12}{'Notes':10}")
    print("-" * (80 + 35 + 12 + 10))
    rules = [r for r in current_app.url_map.iter_rules()]
    rules.sort(key=(lambda r: r.rule))
    for r in rules:
        methods = ", ".join([m for m in r.methods if m not in ["HEAD", "OPTIONS"]])
        requires_gevent = (
            "gevent"
            if hasattr(current_app.view_functions[r.endpoint], "gevent_required")
            else ""
        )
        print(f"{r.rule:80}{r.endpoint:35}{methods:12}{requires_gevent:10}")
