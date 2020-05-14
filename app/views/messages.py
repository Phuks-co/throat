""" Messages endpoints """
from datetime import datetime
from flask import Blueprint, redirect, url_for, render_template
from flask_login import login_required, current_user
from flask_babel import _
from .. import misc
from ..models import Message
from ..socketio import socketio

bp = Blueprint('messages', __name__)


@bp.route("/")
@login_required
def inbox_sort():
    """ Go to inbox with the new message """
    if misc.get_unread_count(misc.MESSAGE_TYPE_PM) > 0:
        return redirect(url_for('messages.view_messages'))
    elif misc.get_unread_count(misc.MESSAGE_TYPE_MENTION) > 0:
        return redirect(url_for('messages.view_mentions'))
    elif misc.get_unread_count(misc.MESSAGE_TYPE_POSTREPLY) > 0:
        return redirect(url_for('messages.view_messages_postreplies'))
    elif misc.get_unread_count(misc.MESSAGE_TYPE_COMMREPLY) > 0:
        return redirect(url_for('messages.view_messages_comreplies'))
    elif misc.get_unread_count(misc.MESSAGE_TYPE_MODMAIL) > 0:
        return redirect(url_for('messages.view_messages_modmail'))
    return redirect(url_for('messages.view_messages'))


@bp.route("/inbox", defaults={'page': 1})
@bp.route("/inbox/<int:page>")
@login_required
def view_messages(page):
    """ View user's messages """
    msgs = misc.getMessagesIndex(page)
    return render_template('messages/messages.html', page=page,
                           messages=msgs, box_name="Inbox", boxID="1",
                           box_route='messages.view_messages')


@bp.route("/mentions", defaults={'page': 1})
@bp.route("/mentions/<int:page>")
@login_required
def view_mentions(page):
    """ View user name mentions """
    Message.update(read=datetime.utcnow()).where(
        (Message.read.is_null(True)) & (Message.mtype == 8) & (Message.receivedby == current_user.uid)).execute()

    msgs = misc.getMentionsIndex(page)
    return render_template('messages/messages.html', page=page,
                           messages=msgs, box_name=_("Mentions"), boxID="8",
                           box_route='messages.view_mentions')


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


@bp.route("/postreplies", defaults={'page': 1})
@bp.route("/postreplies/<int:page>")
@login_required
def view_messages_postreplies(page):
    """ WIP: View user's post replies """
    Message.update(read=datetime.utcnow()).where(
        (Message.read.is_null(True)) & (Message.mtype == 4) & (Message.receivedby == current_user.uid)).execute()

    socketio.emit('notification',
                  {'count': current_user.notifications},
                  namespace='/snt',
                  room='user' + current_user.uid)
    msgs = misc.getMsgPostReplies(page)
    return render_template('messages/postreply.html', messages=msgs,
                           page=page, box_name=_("Replies"), boxID="2",
                           box_route='messages.view_messages_postreplies')


@bp.route("/commentreplies", defaults={'page': 1})
@bp.route("/commentreplies/<int:page>")
@login_required
def view_messages_comreplies(page):
    """ WIP: View user's comments replies """
    Message.update(read=datetime.utcnow()).where(
        (Message.read.is_null(True)) & (Message.mtype == 5) & (Message.receivedby == current_user.uid)).execute()
    socketio.emit('notification',
                  {'count': current_user.notifications},
                  namespace='/snt',
                  room='user' + current_user.uid)
    msgs = misc.getMsgCommReplies(page)
    return render_template('messages/commreply.html',
                           page=page, box_name=_("Replies"), messages=msgs,
                           box_route='messages.view_messages_comreplies')


@bp.route("/modmail", defaults={'page': 1})
@bp.route("/modmail/<int:page>")
@login_required
def view_messages_modmail(page):
    """ WIP: View user's modmail """
    msgs = misc.getMessagesModmail(page)
    return render_template('messages/modmail.html', messages=msgs,
                           page=page, box_route='messages.view_messages_modmail')


@bp.route("/saved", defaults={'page': 1})
@bp.route("/saved/<int:page>")
@login_required
def view_saved_messages(page):
    """ WIP: View user's saved messages """
    msgs = misc.getMessagesSaved(page)
    return render_template('messages/saved.html', messages=msgs,
                           page=page, box_route='messages.view_saved_messages')
