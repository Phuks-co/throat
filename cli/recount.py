import click
from flask.cli import AppGroup
from app.models import Sub, SubSubscriber

recount = AppGroup("recount", help="Re-count various internal counters")


@recount.command(help="Rebuilds all sub's subscriber counters")
@click.option(
    "--save/--dry-run",
    default=True,
    help="Use --save (the default) to fix the counts, or --dry-run to just print them.",
)
def subscribers(save):
    """Update subscriber counts for all the subs."""
    if save:
        print("Name                             Before   After")
    else:
        print("Name                            Current Correct")

    subs = Sub.select(Sub.sid, Sub.name, Sub.subscribers).order_by(Sub.name)
    for sub in subs:
        count = (
            SubSubscriber.select()
            .where((SubSubscriber.sid == sub.sid) & (SubSubscriber.status == 1))
            .count()
        )
        print(f"{sub.name:32}{sub.subscribers:7}{count:8}")
        if save:
            Sub.update(
                subscribers=SubSubscriber.select()
                .where((SubSubscriber.sid == sub.sid) & (SubSubscriber.status == 1))
                .count()
            ).where(Sub.sid == sub.sid).execute()
