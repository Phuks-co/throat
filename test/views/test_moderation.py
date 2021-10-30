import json
import re
from bs4 import BeautifulSoup
from flask import url_for

from app.config import config
from test.utilities import (
    create_sub,
    csrf_token,
    log_in_user,
    log_out_current_user,
    promote_user_to_admin,
    register_user,
)


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
