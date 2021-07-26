import json
import pytest
from bs4 import BeautifulSoup
from flask import url_for

from app.misc import get_notification_count
from app.config import config
from app.models import User
from test.utilities import (
    create_sub,
    csrf_token,
    log_in_user,
    log_out_current_user,
    promote_user_to_admin,
    register_user,
)


@pytest.mark.parametrize("sub_mod", ["sender", "receiver", "neither"])
def test_reply_notification(client, sub_mod, user_info, user2_info, user3_info):
    "Notifications are sent for post and comment replies."
    sender, receiver, mod = user_info, user2_info, user3_info
    config.update_value("site.sub_creation_min_level", 0)

    register_user(client, sender)
    sender_uid = User.get(User.name == sender["username"]).uid
    if sub_mod == "sender":
        create_sub(client)
    log_out_current_user(client)

    register_user(client, receiver)
    receiver_uid = User.get(User.name == receiver["username"]).uid
    if sub_mod == "receiver":
        create_sub(client)
    log_out_current_user(client)

    if sub_mod == "neither":
        register_user(client, mod)
        create_sub(client)
        log_out_current_user(client)

    # Receiver makes a post that can be replied to
    log_in_user(client, receiver)
    rv = client.get(url_for("subs.submit", ptype="text", sub="test"))
    csrf = csrf_token(rv.data)
    data = {
        "csrf_token": csrf,
        "title": "the title",
        "ptype": "text",
        "content": "the content",
    }
    rv = client.post(
        url_for("subs.submit", ptype="text", sub="test"),
        data=data,
        follow_redirects=False,
    )
    assert rv.status == "302 FOUND"
    soup = BeautifulSoup(rv.data, "html.parser", from_encoding="utf-8")
    link = soup.a.get_text()
    pid = link.split("/")[-1]

    # Receiver makes a comment that can be replied to.
    rv = client.get(link, follow_redirects=True)
    assert b"the title |  test" in rv.data
    data = {
        "csrf_token": csrf,
        "post": pid,
        "parent": "0",
        "comment": "OP reply",
    }
    rv = client.post(
        url_for("do.create_comment", pid=pid), data=data, follow_redirects=False
    )
    reply = json.loads(rv.data.decode("utf-8"))
    assert reply["status"] == "ok"
    cid = reply["cid"]

    # Receiver blocks sender.
    data = {
        "csrf_token": csrf,
        "view_messages": "show",
        "view_content": "hide",
    }
    rv = client.post(
        url_for("do.edit_ignore", uid=sender_uid), data=data, follow_redirects=True
    )
    reply = json.loads(rv.data.decode("utf-8"))
    assert reply["status"] == "ok"
    log_out_current_user(client)

    # Sender replies to the post.
    log_in_user(client, sender)
    rv = client.get(link, follow_redirects=True)
    assert b"the title |  test" in rv.data
    data = {
        "csrf_token": csrf,
        "post": pid,
        "parent": "0",
        "comment": "the comment",
    }
    rv = client.post(
        url_for("do.create_comment", pid=pid), data=data, follow_redirects=True
    )
    assert b"the comment" in rv.data

    # Sender replies to the comment.
    rv = client.get(link, follow_redirects=True)
    data = {
        "csrf_token": csrf_token(rv.data),
        "post": pid,
        "parent": cid,
        "comment": "comment reply",
    }
    rv = client.post(
        url_for("do.create_comment", pid=pid), data=data, follow_redirects=True
    )
    log_out_current_user(client)

    # Depending on who is the mod of the sub, should these notifications
    # be visible when the receiver has the sender blocked?
    expected = {"sender": True, "receiver": True, "neither": False}[sub_mod]
    assert get_notification_count(receiver_uid)["notifications"] == (
        2 if expected else 0
    )

    # Receiver checks notifications.
    log_in_user(client, receiver)
    rv = client.get(url_for("messages.view_notifications"))
    assert (b"replied to your post" in rv.data) == expected
    assert (b"the comment" in rv.data) == expected
    assert (b"replied to your comment" in rv.data) == expected
    assert (b"comment reply" in rv.data) == expected

    # Receiver unblocks sender.
    data = {
        "csrf_token": csrf,
        "view_messages": "show",
        "view_content": "show",
    }
    rv = client.post(
        url_for("do.edit_ignore", uid=sender_uid), data=data, follow_redirects=True
    )
    reply = json.loads(rv.data.decode("utf-8"))
    assert reply["status"] == "ok"

    # Receiver checks notifications.
    rv = client.get(url_for("messages.view_notifications"))
    assert b"replied to your post" in rv.data
    assert b"the comment" in rv.data
    assert b"replied to your comment" in rv.data
    assert b"comment reply" in rv.data

    # Notifications should be marked read.
    assert get_notification_count(receiver_uid)["notifications"] == 0


@pytest.mark.parametrize("sub_mod", ["sender", "receiver", "neither"])
def test_mention_notification(client, sub_mod, user_info, user2_info, user3_info):
    "Notifications are sent for mentions in posts and comments."
    config.update_value("site.sub_creation_min_level", 0)
    sender, receiver, mod = user_info, user2_info, user3_info

    register_user(client, sender)
    sender_uid = User.get(User.name == sender["username"]).uid
    if sub_mod == "sender":
        create_sub(client)
    log_out_current_user(client)

    register_user(client, receiver)
    receiver_uid = User.get(User.name == receiver["username"]).uid
    if sub_mod == "receiver":
        create_sub(client)
    log_out_current_user(client)

    if sub_mod == "neither":
        register_user(client, mod)
        create_sub(client)
        log_out_current_user(client)

    # Sender makes a post mentioning receiver.
    log_in_user(client, sender)
    rv = client.get(url_for("subs.submit", ptype="text", sub="test"))
    csrf = csrf_token(rv.data)
    data = {
        "csrf_token": csrf,
        "title": "the title",
        "ptype": "text",
        "content": "post about /u/" + receiver["username"],
    }
    rv = client.post(
        url_for("subs.submit", ptype="text", sub="test"),
        data=data,
        follow_redirects=False,
    )
    assert rv.status == "302 FOUND"
    soup = BeautifulSoup(rv.data, "html.parser", from_encoding="utf-8")
    link = soup.a.get_text()
    pid = link.split("/")[-1]

    # Sender makes a comment mentioning receiver.
    rv = client.get(link, follow_redirects=True)
    assert b"the title |  test" in rv.data
    data = {
        "csrf_token": csrf,
        "post": pid,
        "parent": "0",
        "comment": "comment about /u/" + receiver["username"],
    }
    rv = client.post(
        url_for("do.create_comment", pid=pid), data=data, follow_redirects=False
    )
    reply = json.loads(rv.data.decode("utf-8"))
    assert reply["status"] == "ok"
    log_out_current_user(client)

    # Receiver blocks sender.
    log_in_user(client, receiver)
    data = {
        "csrf_token": csrf,
        "view_messages": "show",
        "view_content": "hide",
    }
    rv = client.post(
        url_for("do.edit_ignore", uid=sender_uid), data=data, follow_redirects=True
    )
    reply = json.loads(rv.data.decode("utf-8"))
    assert reply["status"] == "ok"

    # Depending on who is the mod of the sub, should this notification
    # be visible when the receiver has the sender blocked?
    expected = {"sender": True, "receiver": True, "neither": False}[sub_mod]

    # Receiver checks notifications.
    assert get_notification_count(receiver_uid)["notifications"] == (
        2 if expected else 0
    )
    rv = client.get(url_for("messages.view_notifications"))
    assert (b"mentioned you" in rv.data) == expected
    assert (b"post about" in rv.data) == expected
    assert (b"comment about" in rv.data) == expected

    # After checking, the notifications if any are marked read.
    assert get_notification_count(receiver_uid)["notifications"] == 0

    # Receiver unblocks sender.
    data = {
        "csrf_token": csrf_token(rv.data),
        "view_messages": "show",
        "view_content": "show",
    }
    rv = client.post(
        url_for("do.edit_ignore", uid=sender_uid), data=data, follow_redirects=True
    )
    reply = json.loads(rv.data.decode("utf-8"))
    assert reply["status"] == "ok"

    # Receiver checks notifications again.
    rv = client.get(url_for("messages.view_notifications"))
    assert b"mentioned you" in rv.data
    assert b"post about" in rv.data
    assert b"comment about" in rv.data


def test_ban_notification(client, user_info, user2_info):
    "Notifications are sent for sub bans."
    config.update_value("site.sub_creation_min_level", 0)
    receiver, mod = user_info, user2_info

    register_user(client, receiver)
    receiver_uid = User.get(User.name == receiver["username"]).uid
    log_out_current_user(client)

    register_user(client, mod)
    mod_uid = User.get(User.name == mod["username"]).uid
    create_sub(client)
    log_out_current_user(client)

    # Receiver blocks mod.
    log_in_user(client, receiver)
    rv_index = client.get(url_for("home.index", sub="test"))
    csrf = csrf_token(rv_index.data)
    data = {
        "csrf_token": csrf,
        "view_messages": "show",
        "view_content": "hide",
    }
    rv = client.post(
        url_for("do.edit_ignore", uid=mod_uid), data=data, follow_redirects=True
    )
    reply = json.loads(rv.data.decode("utf-8"))
    assert reply["status"] == "ok"
    log_out_current_user(client)

    # Mod bans receiver.
    log_in_user(client, mod)
    data = {
        "csrf_token": csrf,
        "user": receiver["username"],
        "reason": "serious reason",
        "expires": None,
    }
    rv = client.post(
        url_for("do.ban_user_sub", sub="test"),
        data=data,
    )
    reply = json.loads(rv.data.decode("utf-8"))
    assert reply["status"] == "ok"

    # Mod un-bans receiver.
    rv = client.post(
        url_for("do.remove_sub_ban", sub="test", user=receiver["username"]),
        data={"csrf_token": csrf},
    )
    reply = json.loads(rv.data.decode("utf-8"))
    assert reply["status"] == "ok"
    log_out_current_user(client)

    # Receiver checks notifications.  They should not be ignored,
    # because they are mod actions.
    log_in_user(client, receiver)
    assert get_notification_count(receiver_uid)["notifications"] == 2
    rv = client.get(url_for("messages.view_notifications"))
    assert b"banned you from" in rv.data
    assert b"serious reason" in rv.data
    assert b"unbanned you from" in rv.data

    # After checking, the notification is marked read.
    assert get_notification_count(receiver_uid)["notifications"] == 0

    # Receiver unblocks mod.
    data = {
        "csrf_token": csrf_token(rv.data),
        "view_messages": "show",
        "view_content": "show",
    }
    rv = client.post(
        url_for("do.edit_ignore", uid=mod_uid), data=data, follow_redirects=True
    )
    reply = json.loads(rv.data.decode("utf-8"))
    assert reply["status"] == "ok"

    # Receiver checks notifications again.
    rv = client.get(url_for("messages.view_notifications"))
    assert b"banned you from" in rv.data
    assert b"serious reason" in rv.data
    assert b"unbanned you from" in rv.data


def test_post_delete_notification(client, user_info, user2_info, user3_info):
    "Notifications are sent for post delete and undelete."
    config.update_value("site.sub_creation_min_level", 0)
    receiver, admin, mod = user_info, user2_info, user3_info

    register_user(client, receiver)
    receiver_uid = User.get(User.name == receiver["username"]).uid
    log_out_current_user(client)

    register_user(client, admin)
    promote_user_to_admin(client, admin)
    log_out_current_user(client)

    register_user(client, mod)
    mod_uid = User.get(User.name == mod["username"]).uid
    create_sub(client)
    log_out_current_user(client)

    # Receiver makes a post.
    log_in_user(client, receiver)
    rv_post = client.get(url_for("subs.submit", ptype="text", sub="test"))
    csrf = csrf_token(rv_post.data)
    data = {
        "csrf_token": csrf,
        "title": "the title",
        "ptype": "text",
        "content": "the content",
    }
    rv = client.post(
        url_for("subs.submit", ptype="text", sub="test"),
        data=data,
        follow_redirects=False,
    )
    assert rv.status == "302 FOUND"
    soup = BeautifulSoup(rv.data, "html.parser", from_encoding="utf-8")
    link = soup.a.get_text()
    pid = link.split("/")[-1]
    log_out_current_user(client)

    # Mod deletes the post.
    log_in_user(client, mod)
    data = {
        "csrf_token": csrf,
        "post": pid,
        "reason": "serious reason",
        "send_to_admin": False,
    }
    rv = client.post(
        url_for("do.delete_post"),
        data=data,
    )
    reply = json.loads(rv.data.decode("utf-8"))
    assert reply["status"] == "ok"
    log_out_current_user(client)

    # Admin un-deletes the post.
    log_in_user(client, admin)
    data = {
        "csrf_token": csrf,
        "post": pid,
        "reason": "frivolous reason",
    }
    rv = client.post(
        url_for("do.undelete_post"),
        data=data,
    )
    reply = json.loads(rv.data.decode("utf-8"))
    assert reply["status"] == "ok"
    log_out_current_user(client)

    # Receiver blocks mod.
    log_in_user(client, receiver)
    data = {
        "csrf_token": csrf,
        "view_messages": "show",
        "view_content": "hide",
    }
    rv = client.post(
        url_for("do.edit_ignore", uid=mod_uid), data=data, follow_redirects=True
    )
    reply = json.loads(rv.data.decode("utf-8"))
    assert reply["status"] == "ok"

    # Receiver checks notifications.  They should not be ignored,
    # because they are mod actions.
    assert get_notification_count(receiver_uid)["notifications"] == 2
    rv = client.get(url_for("messages.view_notifications"))
    assert b" deleted your post" in rv.data
    assert b"un-deleted your post" in rv.data
    assert b"serious reason" in rv.data
    assert b"frivolous reason" in rv.data

    # After checking, the notification is marked read.
    assert get_notification_count(receiver_uid)["notifications"] == 0

    # Receiver unblocks mod.
    data = {
        "csrf_token": csrf_token(rv.data),
        "view_messages": "show",
        "view_content": "show",
    }
    rv = client.post(
        url_for("do.edit_ignore", uid=mod_uid), data=data, follow_redirects=True
    )
    reply = json.loads(rv.data.decode("utf-8"))
    assert reply["status"] == "ok"

    # Receiver checks notifications again.
    rv = client.get(url_for("messages.view_notifications"))
    assert b" deleted your post" in rv.data
    assert b"un-deleted your post" in rv.data
    assert b"serious reason" in rv.data
    assert b"frivolous reason" in rv.data


def test_mod_invite_notification(client, user_info, user2_info):
    "Notifications are sent for mod invites."
    config.update_value("site.sub_creation_min_level", 0)
    receiver, mod = user_info, user2_info

    register_user(client, receiver)
    receiver_uid = User.get(User.name == receiver["username"]).uid
    log_out_current_user(client)

    register_user(client, mod)
    mod_uid = User.get(User.name == mod["username"]).uid
    create_sub(client, name="test_janitor")
    create_sub(client, name="test_mod")

    # Mod invites receiver as moderator.
    rv_index = client.get(url_for("home.index", sub="test_mod"))
    data = {
        "csrf_token": csrf_token(rv_index.data),
        "user": receiver["username"],
        "level": "1",
    }
    rv = client.post(
        url_for("do.inv_mod", sub="test_mod"),
        data=data,
    )
    reply = json.loads(rv.data.decode("utf-8"))
    assert reply["status"] == "ok"

    # Mod invites receiver as janitor.
    data = {
        "csrf_token": csrf_token(rv_index.data),
        "user": receiver["username"],
        "level": "2",
    }
    rv = client.post(
        url_for("do.inv_mod", sub="test_janitor"),
        data=data,
    )
    reply = json.loads(rv.data.decode("utf-8"))
    assert reply["status"] == "ok"
    log_out_current_user(client)

    # Receiver blocks mod.
    log_in_user(client, receiver)
    data = {
        "csrf_token": csrf_token(rv_index.data),
        "view_messages": "show",
        "view_content": "hide",
    }
    rv = client.post(
        url_for("do.edit_ignore", uid=mod_uid), data=data, follow_redirects=True
    )
    reply = json.loads(rv.data.decode("utf-8"))
    assert reply["status"] == "ok"

    # Receiver checks notifications.  They should not be ignored,
    # because they are mod actions.
    assert get_notification_count(receiver_uid)["notifications"] == 2
    rv = client.get(url_for("messages.view_notifications"))
    assert b"invited you to moderate" in rv.data
    soup = BeautifulSoup(rv.data, "html.parser", from_encoding="utf-8")
    assert soup.find(href=url_for("sub.edit_sub_mods", sub="test_mod"))
    assert soup.find(href=url_for("sub.edit_sub_mods", sub="test_janitor"))

    # After checking, the notification is marked read.
    assert get_notification_count(receiver_uid)["notifications"] == 0

    # Receiver unblocks mod.
    data = {
        "csrf_token": csrf_token(rv.data),
        "view_messages": "show",
        "view_content": "show",
    }
    rv = client.post(
        url_for("do.edit_ignore", uid=mod_uid), data=data, follow_redirects=True
    )
    reply = json.loads(rv.data.decode("utf-8"))
    assert reply["status"] == "ok"

    # Receiver checks notifications again.
    rv = client.get(url_for("messages.view_notifications"))
    assert b"invited you to moderate" in rv.data
    assert soup.find(href=url_for("sub.edit_sub_mods", sub="test_mod"))
    assert soup.find(href=url_for("sub.edit_sub_mods", sub="test_janitor"))
