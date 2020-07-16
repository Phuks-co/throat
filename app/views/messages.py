""" Messages endpoints """
from datetime import datetime
from peewee import JOIN
from flask import Blueprint, redirect, url_for, render_template, abort, jsonify
from flask_login import login_required, current_user
from flask_babel import _
from .. import misc
from ..misc import engine
from ..models import Message, Notification, Sub, SubPost, SubPostComment, User, SubPostCommentVote, UserIgnores
from ..socketio import socketio

bp = Blueprint('messages', __name__)


@bp.route("/")
@login_required
def inbox_sort():
    """ Go to inbox with the new message """
    if misc.get_unread_count(misc.MESSAGE_TYPE_PM) > 0:
        return redirect(url_for('messages.view_messages'))
    elif misc.get_notif_count():
        return redirect(url_for('messages.view_notifications'))
    return redirect(url_for('messages.view_messages'))


@bp.route("/notifications", defaults={'page': 1})
@bp.route("/notifications/<int:page>")
@login_required
def view_notifications(page):
    # Monster query
    ParentComment = SubPostComment.alias()
    notifications = Notification \
        .select(Notification.id, Notification.type, Notification.read, Notification.created, Sub.name.alias('sub_name'),
                Notification.post.alias('pid'), Notification.comment.alias('cid'), User.name.alias('sender'),
                Notification.sender.alias('senderuid'), Notification.content,
                SubPost.title.alias('post_title'), SubPostComment.content.alias('comment_content'),
                SubPostComment.score.alias('comment_score'),
                SubPostComment.content.alias('post_comment'), SubPostCommentVote.positive.alias('comment_positive'),
                UserIgnores.id.alias("ignored"), ParentComment.content.alias('comment_context'),
                ParentComment.time.alias("comment_context_posted"), ParentComment.score.alias("comment_context_score"),
                SubPost.content.alias('post_content'))\
        .join(Sub, JOIN.LEFT_OUTER).switch(Notification) \
        .join(SubPost, JOIN.LEFT_OUTER).switch(Notification) \
        .join(SubPostComment, JOIN.LEFT_OUTER) \
        .join(SubPostCommentVote, JOIN.LEFT_OUTER, on=(
            (SubPostCommentVote.uid == current_user.uid) & (SubPostCommentVote.cid == SubPostComment.cid))) \
        .switch(Notification).join(User, JOIN.LEFT_OUTER, on=Notification.sender == User.uid) \
        .join(UserIgnores, JOIN.LEFT_OUTER, on=(UserIgnores.uid == current_user.uid) & (UserIgnores.target == User.uid)) \
        .join(ParentComment, JOIN.LEFT_OUTER, on=(SubPostComment.parentcid == ParentComment.cid)) \
        .where((Notification.target == current_user.uid) & (SubPostComment.status.is_null(True))) \
        .order_by(Notification.created.desc()) \
        .paginate(page, 50).dicts()
    notifications = list(notifications)

    Notification.update(read=datetime.utcnow()).where(
        (Notification.read.is_null(True)) & (Notification.target == current_user.uid)).execute()
    return engine.get_template('user/messages/notifications.html').render({'notifications': notifications})


@bp.route("/notifications/delete/<int:mid>", methods=['POST'])
@login_required
def delete_notification(mid):
    try:
        notification = Notification.get((Notification.target == current_user.uid) & (Notification.id == mid))
    except Notification.DoesNotExist:
        return abort(404)
    notification.delete_instance()
    return jsonify(status="ok")


@bp.route("/inbox", defaults={'page': 1})
@bp.route("/inbox/<int:page>")
@login_required
def view_messages(page):
    """ View user's messages """
    msgs = misc.getMessagesIndex(page)
    return render_template('messages/messages.html', page=page,
                           messages=msgs, box_name="Inbox", boxID="1",
                           box_route='messages.view_messages')


@bp.route("/sent", defaults={'page': 1})
@bp.route("/sent/<int:page>")
@login_required
def view_messages_sent(page):
    """ View user's messages sent """
    msgs = misc.getMessagesSent(page)
    return render_template('messages/sent.html', messages=msgs,
                           page=page, box_route='messages.view_messages_sent')


@bp.route("/ignore")
@login_required
def view_ignores():
    """ View user's messages sent """
    igns = misc.get_ignores(current_user.uid)
    return render_template('messages/ignores.html', igns=igns)


@bp.route("/saved", defaults={'page': 1})
@bp.route("/saved/<int:page>")
@login_required
def view_saved_messages(page):
    """ WIP: View user's saved messages """
    msgs = misc.getMessagesSaved(page)
    return render_template('messages/saved.html', messages=msgs,
                           page=page, box_route='messages.view_saved_messages')
