""" Messages endpoints """
from flask import Blueprint, redirect, url_for, render_template, abort, jsonify
from flask_login import login_required, current_user
from .. import misc
from ..notifications import Notifications
from ..misc import engine, get_postmeta_dicts
from ..models import Notification

bp = Blueprint("messages", __name__)


@bp.route("/")
@login_required
def inbox_sort():
    """Go to inbox with the new message"""
    if misc.get_unread_count() > 0:
        return redirect(url_for("messages.view_messages"))
    elif misc.get_notif_count():
        return redirect(url_for("messages.view_notifications"))
    return redirect(url_for("messages.view_messages"))


@bp.route("/notifications", defaults={"page": 1})
@bp.route("/notifications/<int:page>")
@login_required
def view_notifications(page):
    notifications = Notifications.get_notifications(current_user.uid, page)
    # TODO: Move `lock-comments` to SubPost
    postmeta = get_postmeta_dicts(
        (n["pid"] for n in notifications if n["pid"] is not None)
    )

    for n in notifications:
        n["archived"] = False
        if n["cid"] or (n["pid"] and n["type"] not in ("POST_DELETE", "POST_UNDELETE")):
            n["archived"] = misc.is_archived(n)
            misc.add_blur(n)
        if (
            n["cid"]
            and n["already_viewed"] is not None
            and n["posted"] > misc.get_best_comment_sort_init_date()
            and not n["archived"]
        ):
            n["unseen"] = "unseen-comment"
        else:
            n["unseen"] = ""

    Notifications.mark_read(current_user.uid, notifications)
    return engine.get_template("user/messages/notifications.html").render(
        {"notifications": notifications, "postmeta": postmeta}
    )


@bp.route("/notifications/delete/<int:mid>", methods=["POST"])
@login_required
def delete_notification(mid):
    try:
        notification = Notification.get(
            (Notification.target == current_user.uid) & (Notification.id == mid)
        )
    except Notification.DoesNotExist:
        return abort(404)
    notification.delete_instance()
    return jsonify(status="ok")


@bp.route("/inbox", defaults={"page": 1})
@bp.route("/inbox/<int:page>")
@login_required
def view_messages(page):
    """View user's messages"""
    msgs = misc.get_messages_inbox(page)
    return render_template(
        "messages/messages.html",
        page=page,
        messages=msgs,
        box_name="Inbox",
        box_route="messages.view_messages",
    )


@bp.route("/sent", defaults={"page": 1})
@bp.route("/sent/<int:page>")
@login_required
def view_messages_sent(page):
    """View user's messages sent"""
    msgs = misc.get_messages_sent(page)
    return render_template(
        "messages/sent.html",
        messages=msgs,
        page=page,
        box_route="messages.view_messages_sent",
    )


@bp.route("/saved", defaults={"page": 1})
@bp.route("/saved/<int:page>")
@login_required
def view_saved_messages(page):
    """WIP: View user's saved messages"""
    msgs = misc.get_messages_saved(page)
    return render_template(
        "messages/saved.html",
        messages=msgs,
        page=page,
        box_route="messages.view_saved_messages",
    )
