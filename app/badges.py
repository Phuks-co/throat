""" Here we store badges. """
from .storage import FILE_NAMESPACE, mtype_from_file, calculate_file_hash, store_file
from peewee import JOIN
from .models import Badge, UserMetadata, SubMod
from flask_babel import lazy_gettext as _l
import uuid


class Badges:
    """
    Badge exposes a stable API for dealing with user badges.

    We need to be able to look up a badge by id and name, along with the ability to
    iterate through all of the badges.

    We also want to be able to create badges.

    For backwards compatability we will allow "fetching" of old_badges but only by ID.

    This will also create an interfact for Triggers, as Badges and Triggers are interlinked.
    """

    def __iter__(self):
        """
        Returns a list of all bagdes in the database.
        """
        return (x for x in Badge.select(Badge.bid, Badge.name, Badge.alt, Badge.icon, Badge.score, Badge.trigger, Badge.rank)
                .order_by(Badge.rank, Badge.name))

    def __getitem__(self, bid):
        """
        Returns a badge from the database.
        """
        try:
            return Badge.get(Badge.bid == bid)
        except:
            return None

    def update_badge(self, bid, name, alt, icon, score, rank, trigger):
        """
        Updates the information related to a badge, updates icon if provided.
        """
        if icon:
            icon = gen_icon(icon)
        else:
            icon = self[bid].icon

        Badge.update(name=name, alt=alt, icon=icon, score=score,
                     rank=rank, trigger=trigger).where(Badge.bid == bid).execute()

    def new_badge(self, name, alt, icon, score, rank, trigger=None):
        """
        Creates a new badge with an optional trigger.
        """
        icon = gen_icon(icon)
        Badge.create(name=name, alt=alt, icon=icon,
                     score=score, rank=rank, trigger=trigger)

    def delete_badge(self, bid):
        """
        Deletes a badge by ID
        """
        Badge.delete().where(Badge.bid == bid).execute()
        UserMetadata.delete().where((UserMetadata.key == 'badge')
                                    & (UserMetadata.value == bid)).execute()

    def assign_userbadge(self, uid, bid):
        """
        Gives a badge to a user
        """
        UserMetadata.get_or_create(key="badge", uid=uid, value=bid)

    def unassign_userbadge(self, uid, bid):
        """
        Removes a badge from a user
        """
        UserMetadata.delete().where((UserMetadata.key == "badge") & (
            UserMetadata.uid == uid) & (UserMetadata.value == str(bid))).execute()

    def triggers(self):
        """
        Lists available triggers that can be attached to a badge.
        """
        return triggers.keys()

    def badges_for_user(self, uid):
        """
        Returns a list of badges associated with a user.
        """
        return Badge.select(Badge.bid, Badge.name, Badge.icon, Badge.score, Badge.alt, Badge.rank)\
            .join(UserMetadata, JOIN.LEFT_OUTER, on=(UserMetadata.value.cast("int") == Badge.bid))\
            .where((UserMetadata.uid == uid) & (UserMetadata.key == 'badge'))\
            .order_by(Badge.rank, Badge.name)


def gen_icon(icon):
    mtype = mtype_from_file(icon, allow_video_formats=False)
    if mtype is None:
        raise Exception(
            _l('Invalid file type. Only jpg, png and gif allowed.'))

    fhash = calculate_file_hash(icon)
    basename = str(uuid.uuid5(FILE_NAMESPACE, fhash))
    f_name = store_file(icon, basename, mtype, remove_metadata=True)
    return f_name


badges = Badges()


def admin(bid):
    """
    Auto assigns badges to admins.
    """
    for user in UserMetadata.select().where((UserMetadata.key == "admin") & (UserMetadata.value == '1')):
        print("Giving ",bid," to:", user.uid)
        badges.assign_userbadge(user.uid, bid)


def mod(bid):
    """
    Auto assigns badges to mods.
    """
    for user in SubMod.select().where((SubMod.invite == False)):
        print("Giving ", bid ," to:", user.uid)
        badges.assign_userbadge(user.uid, bid)


# TODO actually hook these up
triggers = {
    "admin": admin,
    "mod": mod,
}
