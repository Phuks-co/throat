import json
import re
from bs4 import BeautifulSoup
from flask import url_for
import pytest

from app.config import config
from app.misc import get_notification_count
from app.models import User
from test.utilities import (
    create_sub,
    csrf_token,
    log_in_user,
    log_out_current_user,
    promote_user_to_admin,
    register_user,
)


def test_mod_post_delete(client, user_info, user2_info, user3_info):
    config.update_value("site.sub_creation_min_level", 0)
    user, admin, mod = user_info, user2_info, user3_info
    register_user(client, admin)
    promote_user_to_admin(client, admin)
    log_out_current_user(client)

    register_user(client, mod)
    create_sub(client)
    log_out_current_user(client)

    register_user(client, user)

    # User makes several posts.
    pids = {}
    posts = [
        "delete_user",
        "delete_admin",
        "delete_then_undelete_by_admin",
        "delete_mod",
        "delete_then_undelete_by_mod",
        "delete_undelete_by_mod_then_admin",
    ]
    rv = client.get(url_for("subs.submit", ptype="text", sub="test"))
    csrf = csrf_token(rv.data)
    for post in posts:
        rv = client.post(
            url_for("subs.submit", ptype="text", sub="test"),
            data={
                "csrf_token": csrf,
                "title": post,
                "ptype": "text",
                "content": "the content",
            },
            follow_redirects=False,
        )
        assert rv.status == "302 FOUND"
        soup = BeautifulSoup(rv.data, "html.parser", from_encoding="utf-8")
        link = soup.a.get_text()
        pids[post] = link.split("/")[-1]

    # User can see all the posts.
    rv = client.get(url_for("sub.view_sub", sub="test"), follow_redirects=True)
    data = rv.data.decode("utf-8")
    for post in posts:
        assert post in data

    # User has a delete link on a single-post page.
    rv = client.get(
        url_for("sub.view_post", sub="test", pid=pids["delete_user"]),
        follow_redirects=True,
    )
    assert len(re.findall("[^n]delete-post", rv.data.decode("utf-8"))) == 1

    # User deletes a post.
    rv = client.post(
        url_for("do.delete_post"),
        data={"csrf_token": csrf, "post": pids["delete_user"]},
    )
    reply = json.loads(rv.data.decode("utf-8"))
    assert reply["status"] == "ok"

    # User can now not see deleted post
    rv = client.get(url_for("sub.view_sub", sub="test"), follow_redirects=True)
    data = rv.data.decode("utf-8")
    for post in posts:
        if post == "delete_user":
            assert post not in data
        else:
            assert post in data

    # User can go to deleted post page but there is no delete or undelete link.
    rv = client.get(
        url_for("sub.view_post", sub="test", pid=pids["delete_user"]),
        follow_redirects=True,
    )
    data = rv.data.decode("utf-8")
    assert "the content" not in data
    assert len(re.findall("delete-post", data)) == 0

    log_out_current_user(client)

    # Admin sees deleted post content, and no delete or undelete link.
    log_in_user(client, admin)
    rv = client.get(
        url_for("sub.view_post", sub="test", pid=pids["delete_user"]),
        follow_redirects=True,
    )
    data = rv.data.decode("utf-8")
    assert "the content" in data
    assert len(re.findall("delete-post", data)) == 0

    # Admin tries to remove user's deleted post.
    rv = client.post(
        url_for("do.delete_post"),
        data={"csrf_token": csrf, "post": pids["delete_user"]},
    )
    reply = json.loads(rv.data.decode("utf-8"))
    assert reply["status"] == "error"
    assert reply["error"] == ["Post was already deleted"]

    # Admin deletes two posts.
    for post in ["delete_admin", "delete_then_undelete_by_admin"]:
        rv = client.post(
            url_for("do.delete_post"),
            data={"csrf_token": csrf, "post": pids[post], "reason": "admin"},
        )
        reply = json.loads(rv.data.decode("utf-8"))
        assert reply["status"] == "ok"

    # Admin can still see the post content and now has undelete links.
    for post in ["delete_admin", "delete_then_undelete_by_admin"]:
        rv = client.get(
            url_for("sub.view_post", sub="test", pid=pids[post]), follow_redirects=True
        )
        data = rv.data.decode("utf-8")
        assert "the content" in data
        # Check for the css class on the bottombar delete links.
        assert len(re.findall("undelete-post", data)) == 1
        assert len(re.findall("[^n]delete-post", data)) == 0

    # Admin undeletes a post.
    rv = client.post(
        url_for("do.undelete_post"),
        data={
            "csrf_token": csrf,
            "post": pids["delete_then_undelete_by_admin"],
            "reason": "admin",
        },
    )
    reply = json.loads(rv.data.decode("utf-8"))
    assert reply["status"] == "ok"
    log_out_current_user(client)

    # Mod can see content of all posts.  Mod sees delete links for the
    # posts which are not deleted, and does not have delete or
    # undelete links for the deleted posts.
    log_in_user(client, mod)
    for post in posts:
        rv = client.get(
            url_for("sub.view_post", sub="test", pid=pids[post]), follow_redirects=True
        )
        data = rv.data.decode("utf-8")
        assert post in data
        assert "the content" in data
        if post in ["delete_user", "delete_admin"]:
            assert len(re.findall("delete-post", data)) == 0
        else:
            assert len(re.findall("undelete-post", data)) == 0
            assert len(re.findall("[^n]delete-post", data)) == 1

    # Mod tries to remove already deleted posts.
    for post in ["delete_user", "delete_admin"]:
        rv = client.post(
            url_for("do.delete_post"),
            data={"csrf_token": csrf, "post": pids[post], "reason": "mod"},
        )
        reply = json.loads(rv.data.decode("utf-8"))
        assert reply["status"] == "error"
        assert reply["error"] == ["Post was already deleted"]

    # Mod can't undelete post deleted by admin.
    rv = client.post(
        url_for("do.undelete_post"),
        data={"csrf_token": csrf, "post": pids["delete_admin"], "reason": "mod"},
    )
    reply = json.loads(rv.data.decode("utf-8"))
    assert reply["status"] == "error"
    assert reply["error"] == ["Not authorized"]

    # Mod deletes some posts.
    for post in [
        "delete_mod",
        "delete_then_undelete_by_mod",
        "delete_undelete_by_mod_then_admin",
    ]:
        rv = client.post(
            url_for("do.delete_post"),
            data={"csrf_token": csrf, "post": pids[post], "reason": "mod"},
        )
        reply = json.loads(rv.data.decode("utf-8"))
        assert reply["status"] == "ok"

    # Mod sees content of all posts, and now has two undelete links.
    for post in posts:
        rv = client.get(
            url_for("sub.view_post", sub="test", pid=pids[post]), follow_redirects=True
        )
        data = rv.data.decode("utf-8")
        assert post in data
        assert "the content" in data
        if post in ["delete_user", "delete_admin"]:
            assert len(re.findall("delete-post", data)) == 0
        elif post in [
            "delete_mod",
            "delete_then_undelete_by_mod",
            "delete_undelete_by_mod_then_admin",
        ]:
            assert len(re.findall("[^n]delete-post", data)) == 0
            assert len(re.findall("undelete-post", data)) == 1
        else:
            assert len(re.findall("undelete-post", data)) == 0
            assert len(re.findall("[^n]delete-post", data)) == 1

    # Mod undeletes a post.
    rv = client.post(
        url_for("do.undelete_post"),
        data={
            "csrf_token": csrf,
            "post": pids["delete_then_undelete_by_mod"],
            "reason": "mod",
        },
    )
    reply = json.loads(rv.data.decode("utf-8"))
    assert reply["status"] == "ok"
    log_out_current_user(client)

    log_in_user(client, admin)
    # Admin has undelete links for the content admin deleted as well as
    # the content the mod deleted.
    for post in posts:
        rv = client.get(
            url_for("sub.view_post", sub="test", pid=pids[post]), follow_redirects=True
        )
        data = rv.data.decode("utf-8")
        assert post in data
        assert "the content" in data
        if post == "delete_user":
            assert len(re.findall("delete-post", data)) == 0
        elif post in [
            "delete_admin",
            "delete_mod",
            "delete_undelete_by_mod_then_admin",
        ]:
            assert len(re.findall("[^n]delete-post", data)) == 0
            assert len(re.findall("undelete-post", data)) == 1
        else:
            assert len(re.findall("undelete-post", data)) == 0
            assert len(re.findall("[^n]delete-post", data)) == 1

    # Admin can undelete a post deleted by the mod.
    rv = client.post(
        url_for("do.undelete_post"),
        data={
            "csrf_token": csrf,
            "post": pids["delete_undelete_by_mod_then_admin"],
            "reason": "admin",
        },
    )
    reply = json.loads(rv.data.decode("utf-8"))
    assert reply["status"] == "ok"
    log_out_current_user(client)

    log_in_user(client, user)
    # User can see posts which were deleted by mod or admin.
    undeleted = [
        "delete_then_undelete_by_admin",
        "delete_then_undelete_by_mod",
        "delete_undelete_by_mod_then_admin",
    ]
    for post in posts:
        rv = client.get(
            url_for("sub.view_post", sub="test", pid=pids[post]), follow_redirects=True
        )
        data = rv.data.decode("utf-8")
        assert post in data
        if post != "delete_user":
            assert "the content" in data
        # User has a delete link for posts which are not deleted, and
        # no undelete links.
        if post in undeleted:
            assert len(re.findall("[^n]delete-post", data)) == 1
        else:
            assert len(re.findall("[^n]delete-post", data)) == 0
        assert len(re.findall("undelete-post", data)) == 0

    for post in posts:
        if post not in undeleted:
            # User can't delete anything which has already been deleted.
            rv = client.post(
                url_for("do.delete_post"),
                data={
                    "csrf_token": csrf,
                    "post": pids["delete_user"],
                    "reason": "user",
                },
            )
            reply = json.loads(rv.data.decode("utf-8"))
            assert reply["status"] == "error"
            assert reply["error"] == ["Post was already deleted"]

    # User can't undelete any posts.
    for post in posts:
        rv = client.post(
            url_for("do.undelete_post"),
            data={"csrf_token": csrf, "post": pids[post], "reason": "user"},
        )
        reply = json.loads(rv.data.decode("utf-8"))
        assert reply["status"] == "error"
        if post == "delete_user":
            assert reply["error"] == ["Can not un-delete a self-deleted post"]
        elif "undelete" in post:
            assert reply["error"] == ["Post is not deleted"]
        else:
            assert reply["error"] == ["Not authorized"]


def test_mod_comment_delete(client, user_info, user2_info, user3_info):
    config.update_value("site.sub_creation_min_level", 0)
    user, admin, mod = user_info, user2_info, user3_info
    register_user(client, admin)
    promote_user_to_admin(client, admin)
    log_out_current_user(client)

    register_user(client, mod)
    create_sub(client)
    log_out_current_user(client)

    register_user(client, user)

    # User makes a post.
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

    # User adds some comments.
    rv = client.get(link, follow_redirects=True)
    assert b"the title |  test" in rv.data
    cids = {}
    comments = [
        "delete_user",
        "delete_admin",
        "delete_then_undelete_by_admin",
        "delete_mod",
        "delete_then_undelete_by_mod",
        "delete_undelete_by_mod_then_admin",
    ]
    for comment in comments:
        data = {
            "csrf_token": csrf,
            "post": pid,
            "parent": "0",
            "comment": comment,
        }
        rv = client.post(
            url_for("do.create_comment", pid=pid), data=data, follow_redirects=False
        )
        reply = json.loads(rv.data.decode("utf-8"))
        assert reply["status"] == "ok"
        cids[comment] = reply["cid"]

    # User reloads the page and can see all the comments.
    rv = client.get(link, follow_redirects=True)
    data = rv.data.decode("utf-8")
    for comment in comments:
        assert comment in data
    # Check for the css class on the bottombar delete links.
    assert len(re.findall("[^n]delete-comment", data)) == len(comments)

    rv = client.post(
        url_for("do.delete_comment"),
        data={"csrf_token": csrf, "cid": cids["delete_user"]},
    )
    reply = json.loads(rv.data.decode("utf-8"))
    assert reply["status"] == "ok"

    # User can no longer see deleted comment.
    rv = client.get(link, follow_redirects=True)
    data = rv.data.decode("utf-8")
    for comment in comments:
        if comment == "delete_user":
            assert comment not in data
        else:
            assert comment in data
    log_out_current_user(client)

    # Admin sees deleted comment content, and n-1 delete links.
    log_in_user(client, admin)
    rv = client.get(link, follow_redirects=True)
    data = rv.data.decode("utf-8")
    for comment in comments:
        assert comment in data
    # Check for the css class on the bottombar delete links.
    assert len(re.findall("[^n]delete-comment", data)) == len(comments) - 1
    assert "undelete-comment" not in data

    # Admin tries to remove user's deleted comment.
    rv = client.post(
        url_for("do.delete_comment"),
        data={"csrf_token": csrf, "cid": cids["delete_user"]},
    )
    reply = json.loads(rv.data.decode("utf-8"))
    assert reply["status"] == "error"
    assert reply["error"] == "Comment is already deleted"

    # Admin removes two comments.
    for comment in ["delete_admin", "delete_then_undelete_by_admin"]:
        rv = client.post(
            url_for("do.delete_comment"),
            data={"csrf_token": csrf, "cid": cids[comment]},
        )
        reply = json.loads(rv.data.decode("utf-8"))
        assert reply["status"] == "ok"

    # Admin can still see all comment content and now has two undelete links.
    rv = client.get(link, follow_redirects=True)
    data = rv.data.decode("utf-8")
    for comment in comments:
        assert comment in data
    # Check for the css class on the bottombar delete links.
    assert len(re.findall("undelete-comment", data)) == 2
    assert len(re.findall("[^n]delete-comment", data)) == len(comments) - 3

    # Admin undeletes a comment.
    rv = client.post(
        url_for("do.undelete_comment"),
        data={"csrf_token": csrf, "cid": cids["delete_then_undelete_by_admin"]},
    )
    reply = json.loads(rv.data.decode("utf-8"))
    assert reply["status"] == "ok"
    log_out_current_user(client)

    # Mod sees content of deleted and undeleted comments.
    log_in_user(client, mod)
    rv = client.get(link, follow_redirects=True)
    data = rv.data.decode("utf-8")
    for comment in comments:
        assert comment in data
    # Mod should see delete links for undeleted comments.
    assert len(re.findall("[^n]delete-comment", data)) == len(comments) - 2
    assert len(re.findall("undelete-comment", data)) == 0

    # Mod tries to remove already deleted comments.
    for comment in ["delete_user", "delete_admin"]:
        rv = client.post(
            url_for("do.delete_comment"),
            data={"csrf_token": csrf, "cid": cids[comment]},
        )
        reply = json.loads(rv.data.decode("utf-8"))
        assert reply["status"] == "error"
        assert reply["error"] == "Comment is already deleted"

    # Mod tries to undelete comment deleted by admin.
    rv = client.post(
        url_for("do.undelete_comment"),
        data={"csrf_token": csrf, "cid": cids["delete_admin"]},
    )
    reply = json.loads(rv.data.decode("utf-8"))
    assert reply["status"] == "error"
    assert reply["error"] == "Not authorized"

    # Mod removes some comments.
    for comment in [
        "delete_mod",
        "delete_then_undelete_by_mod",
        "delete_undelete_by_mod_then_admin",
    ]:
        rv = client.post(
            url_for("do.delete_comment"),
            data={"csrf_token": csrf, "cid": cids[comment]},
        )
        reply = json.loads(rv.data.decode("utf-8"))
        assert reply["status"] == "ok"

    # Mod sees content of all comments, and now has two undelete links.
    rv = client.get(link, follow_redirects=True)
    data = rv.data.decode("utf-8")
    for comment in comments:
        assert comment in data
    # Mod should see delete links for undeleted comments.
    assert len(re.findall("[^n]delete-comment", data)) == len(comments) - 5
    assert len(re.findall("undelete-comment", data)) == 3

    # Mod undeletes a comment.
    rv = client.post(
        url_for("do.undelete_comment"),
        data={"csrf_token": csrf, "cid": cids["delete_then_undelete_by_mod"]},
    )
    reply = json.loads(rv.data.decode("utf-8"))
    assert reply["status"] == "ok"
    log_out_current_user(client)

    log_in_user(client, admin)
    # Admin has undelete links for the content admin deleted as well as
    # the content the mod deleted.
    assert len(re.findall("undelete-comment", data)) == 3

    # Admin can undelete a comment deleted by the mod.
    rv = client.post(
        url_for("do.undelete_comment"),
        data={"csrf_token": csrf, "cid": cids["delete_undelete_by_mod_then_admin"]},
    )
    reply = json.loads(rv.data.decode("utf-8"))
    assert reply["status"] == "ok"
    log_out_current_user(client)

    log_in_user(client, user)
    # User can see comments which are not deleted.
    undeleted = [
        "delete_then_undelete_by_admin",
        "delete_then_undelete_by_mod",
        "delete_undelete_by_mod_then_admin",
    ]
    rv = client.get(link, follow_redirects=True)
    data = rv.data.decode("utf-8")
    for comment in comments:
        if comment in undeleted:
            assert comment in data
        else:
            assert comment not in data

    # User should see delete links for undeleted comments.
    assert len(re.findall("[^n]delete-comment", data)) == len(undeleted)
    assert len(re.findall("undelete-comment", data)) == 0

    # User can't undelete any comment
    for comment in comments:
        rv = client.post(
            url_for("do.undelete_comment"),
            data={"csrf_token": csrf, "cid": cids[comment]},
        )
        reply = json.loads(rv.data.decode("utf-8"))
        assert reply["status"] == "error"
        if comment in undeleted:
            assert reply["error"] == "Comment is not deleted"
        elif comment == "delete_user":
            assert reply["error"] == "Can not un-delete a self-deleted comment"
        else:
            assert reply["error"] == "Not authorized"


def test_ban_notification_messages(client, user_info, user2_info):
    "Notifications are sent for sub bans."
    config.update_value("site.sub_creation_min_level", 0)
    receiver, mod = user_info, user2_info

    register_user(client, receiver)
    receiver_uid = User.get(User.name == receiver["username"]).uid
    log_out_current_user(client)

    register_user(client, mod)
    create_sub(client)

    rv = client.get(url_for("sub.view_sub_bans", sub="test"))
    csrf = csrf_token(rv.data)

    # Mod bans receiver.
    rv = client.post(
        url_for("do.ban_user_sub", sub="test"),
        data=dict(
            csrf_token=csrf,
            user=receiver["username"],
            reason="serious reason",
            expires=None,
        ),
    )
    reply = json.loads(rv.data.decode("utf-8"))
    assert reply["status"] == "ok"

    # Mod un-bans receiver.
    rv = client.post(
        url_for("do.remove_sub_ban", sub="test", user=receiver["username"]),
        data=dict(csrf_token=csrf),
    )
    reply = json.loads(rv.data.decode("utf-8"))
    assert reply["status"] == "ok"
    log_out_current_user(client)

    # Receiver checks messages.  They should not be ignored,
    # because they are mod actions.
    log_in_user(client, receiver)
    assert get_notification_count(receiver_uid)["messages"] == 2
    rv = client.get(url_for("messages.view_messages"))
    assert b"permanently banned" in rv.data
    assert b"serious reason" in rv.data
    assert b"no longer banned" in rv.data


def test_mod_invite_messages(client, user_info, user2_info):
    "Messages are sent for mod invites."
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
    rv = client.post(
        url_for("do.inv_mod", sub="test_mod"),
        data=dict(
            csrf_token=csrf_token(rv_index.data), user=receiver["username"], level="1"
        ),
    )
    reply = json.loads(rv.data.decode("utf-8"))
    assert reply["status"] == "ok"

    # Mod invites receiver as janitor.
    rv = client.post(
        url_for("do.inv_mod", sub="test_janitor"),
        data=dict(
            csrf_token=csrf_token(rv_index.data), user=receiver["username"], level="2"
        ),
    )
    reply = json.loads(rv.data.decode("utf-8"))
    assert reply["status"] == "ok"
    log_out_current_user(client)

    # Receiver blocks mod.
    log_in_user(client, receiver)
    rv = client.post(
        url_for("do.edit_ignore", uid=mod_uid),
        data=dict(
            csrf_token=csrf_token(rv_index.data),
            view_messages="hide",
            view_content="hide",
        ),
        follow_redirects=True,
    )
    reply = json.loads(rv.data.decode("utf-8"))
    assert reply["status"] == "ok"

    # Receiver checks messages.  They should not be blocked,
    # because they are mod messages.
    assert get_notification_count(receiver_uid)["messages"] == 2
    rv = client.get(url_for("messages.view_messages"))
    assert b"invited you to moderate" in rv.data
    soup = BeautifulSoup(rv.data, "html.parser", from_encoding="utf-8")
    assert soup.find(href=url_for("sub.edit_sub_mods", sub="test_mod"))
    assert soup.find(href=url_for("sub.edit_sub_mods", sub="test_janitor"))

    # Receiver unblocks mod.
    rv = client.post(
        url_for("do.edit_ignore", uid=mod_uid),
        data=dict(
            csrf_token=csrf_token(rv.data), view_messages="show", view_content="show"
        ),
        follow_redirects=True,
    )
    reply = json.loads(rv.data.decode("utf-8"))
    assert reply["status"] == "ok"

    # Receiver checks messages again.
    assert get_notification_count(receiver_uid)["messages"] == 2
    rv = client.get(url_for("messages.view_messages"))
    soup = BeautifulSoup(rv.data, "html.parser", from_encoding="utf-8")
    assert b"invited you to moderate" in rv.data
    assert soup.find(href=url_for("sub.edit_sub_mods", sub="test_mod"))
    assert soup.find(href=url_for("sub.edit_sub_mods", sub="test_janitor"))

    # Receiver deletes messages.
    mids = [elem["data-mid"] for elem in soup.find_all(class_="deletemsg")]
    assert len(mids) == 2
    for mid in mids:
        rv = client.post(
            url_for("do.delete_pm", mid=mid), data=dict(csrf_token=csrf_token)
        )
        reply = json.loads(rv.data.decode("utf-8"))
        assert reply["status"] == "ok"
    assert get_notification_count(receiver_uid)["messages"] == 0
    log_out_current_user(client)

    # Mod revokes the invitation.
    log_in_user(client, mod)
    rv = client.post(
        url_for("do.revoke_mod2inv", sub="test_mod", user=receiver["username"]),
        data=dict(csrf_token=csrf_token(rv_index.data)),
    )
    reply = json.loads(rv.data.decode("utf-8"))
    assert reply["status"] == "ok"
    log_out_current_user(client)

    # Receiver checks messages.
    log_in_user(client, receiver)
    assert get_notification_count(receiver_uid)["messages"] == 1
    rv = client.get(url_for("messages.view_messages"), follow_redirects=True)
    assert b"cancelled your invitation" in rv.data


@pytest.mark.parametrize("by_admin", [True, False])
def test_mod_action_messages(client, user_info, user2_info, user3_info, by_admin):
    "Notification messages are sent for content moderation actions."
    config.update_value("site.sub_creation_min_level", 0)
    receiver, admin, mod = user_info, user2_info, user3_info

    # Use usernames that aren't going to be found in notification
    # message text, unlike "mod" and "admin".
    receiver["username"] = "yyyyyy"
    mod["username"] = "xxxxxx"
    admin["username"] = "zzzzzz"

    register_user(client, receiver)
    receiver_uid = User.get(User.name == receiver["username"]).uid
    log_out_current_user(client)

    register_user(client, mod)
    mod_uid = User.get(User.name == mod["username"]).uid
    create_sub(client)
    log_out_current_user(client)

    if by_admin:
        register_user(client, admin)
        admin_uid = User.get(User.name == admin["username"]).uid
        promote_user_to_admin(client, admin)
        create_sub(client, name="adminsub")
        config.update_value("site.admin_sub", "adminsub")
        log_out_current_user(client)
        actor, actor_uid = admin, admin_uid
    else:
        actor, actor_uid = mod, mod_uid

    # Receiver makes a post.
    log_in_user(client, receiver)
    rv = client.get(url_for("subs.submit", ptype="text", sub="test"))
    csrf = csrf_token(rv.data)
    rv = client.post(
        url_for("subs.submit", ptype="text", sub="test"),
        data=dict(
            csrf_token=csrf, title="the title", ptype="text", content="the content"
        ),
        follow_redirects=False,
    )
    assert rv.status == "302 FOUND"
    soup = BeautifulSoup(rv.data, "html.parser", from_encoding="utf-8")
    link = soup.a.get_text()
    pid = link.split("/")[-1]

    # Receiver makes a comment.
    rv = client.get(link, follow_redirects=True)
    assert b"the title |  test" in rv.data
    rv = client.post(
        url_for("do.create_comment", pid=pid),
        data=dict(csrf_token=csrf, post=pid, parent="0", comment="OP reply"),
        follow_redirects=False,
    )
    reply = json.loads(rv.data.decode("utf-8"))
    assert reply["status"] == "ok"
    cid = reply["cid"]
    log_out_current_user(client)

    # Mod or admin deletes and then un-deletes the comment.
    log_in_user(client, actor)
    rv = client.post(
        url_for("do.delete_comment"),
        data=dict(csrf_token=csrf, cid=cid, reason="serious comment reason"),
    )
    reply = json.loads(rv.data.decode("utf-8"))
    assert reply["status"] == "ok"

    rv = client.post(
        url_for("do.undelete_comment"),
        data=dict(csrf_token=csrf, cid=cid, reason="frivolous comment reason"),
    )
    reply = json.loads(rv.data.decode("utf-8"))
    assert reply["status"] == "ok"
    log_out_current_user(client)

    # Receiver checks messages, with and without blocking the mod.
    log_in_user(client, receiver)
    for block in [False] if by_admin else [False, True]:
        if block:
            data = dict(csrf_token=csrf, view_messages="hide", view_content="hide")
            rv = client.post(
                url_for("do.edit_ignore", uid=actor_uid),
                data=data,
                follow_redirects=True,
            )
            reply = json.loads(rv.data.decode("utf-8"))
            assert reply["status"] == "ok"

        config.update_value("site.anonymous_modding", False)
        rv = client.get(url_for("messages.view_messages"))
        if by_admin:
            assert b"The site administrators" in rv.data
            assert b"adminsub" in rv.data
        else:
            assert b"The moderators of" in rv.data

        assert b"as mod of" in rv.data
        assert actor["username"].encode("utf-8") in rv.data

        config.update_value("site.anonymous_modding", True)
        rv = client.get(url_for("messages.view_messages"))
        assert b"by the mods of" in rv.data
        assert actor["username"].encode("utf-8") not in rv.data

        assert b"Moderation action: comment deleted" in rv.data
        assert b"Moderation action: comment restored" in rv.data
        assert b"deleted a comment" in rv.data
        assert b"restored a comment" in rv.data
        assert b"serious comment reason" in rv.data
        assert b"frivolous comment reason" in rv.data

    soup = BeautifulSoup(rv.data, "html.parser", from_encoding="utf-8")
    mids = [elem["data-mid"] for elem in soup.find_all(class_="deletemsg")]
    assert len(mids) == 2

    # Receiver deletes messages.
    for mid in mids:
        rv = client.post(
            url_for("do.delete_pm", mid=mid), data=dict(csrf_token=csrf_token)
        )
        reply = json.loads(rv.data.decode("utf-8"))
        assert reply["status"] == "ok"
    assert get_notification_count(receiver_uid)["messages"] == 0
    log_out_current_user(client)

    # Mod or admin deletes and then un-deletes the post.
    log_in_user(client, actor)
    rv = client.post(
        url_for("do.delete_post"),
        data=dict(csrf_token=csrf, post=pid, reason="serious post reason"),
    )
    reply = json.loads(rv.data.decode("utf-8"))
    assert reply["status"] == "ok"

    rv = client.post(
        url_for("do.undelete_post"),
        data=dict(csrf_token=csrf, post=pid, reason="frivolous post reason"),
    )
    reply = json.loads(rv.data.decode("utf-8"))
    assert reply["status"] == "ok"
    log_out_current_user(client)

    # Receiver checks messages, with and without unblocking the mod.
    log_in_user(client, receiver)
    for unblock in [False] if by_admin else [True, False]:
        if unblock:
            data = dict(csrf_token=csrf, view_messages="show", view_content="show")
            rv = client.post(
                url_for("do.edit_ignore", uid=actor_uid),
                data=data,
                follow_redirects=True,
            )
            reply = json.loads(rv.data.decode("utf-8"))
            assert reply["status"] == "ok"

        assert get_notification_count(receiver_uid)["messages"] == 2

        config.update_value("site.anonymous_modding", False)
        rv = client.get(url_for("messages.view_messages"))
        if by_admin:
            assert b"The site administrators" in rv.data
            assert b"adminsub" in rv.data
        else:
            assert b"The moderators of" in rv.data
        assert b"as mod of" in rv.data
        assert actor["username"].encode("utf-8") in rv.data

        config.update_value("site.anonymous_modding", True)
        rv = client.get(url_for("messages.view_messages"))
        assert b"by the mods of" in rv.data
        assert actor["username"].encode("utf-8") not in rv.data

        assert b"Moderation action: post deleted" in rv.data
        assert b"Moderation action: post restored" in rv.data
        assert b"deleted your post" in rv.data
        assert b"restored your post" in rv.data
        assert b"serious post reason" in rv.data
        assert b"frivolous post reason" in rv.data
