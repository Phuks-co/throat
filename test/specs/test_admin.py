from app.models import SiteMetadata, Sub, SubPost, User
import json
import pytest

from flask import url_for
from app import mail
from app.misc import getAnnouncementPid

from test.utilities import csrf_token, promote_user_to_admin
from test.utilities import register_user, log_in_user, log_out_current_user


def test_admin_can_ban_and_unban_user(client, user_info, user2_info):
    register_user(client, user_info)
    register_user(client, user2_info)
    promote_user_to_admin(client, user2_info)

    username = user_info["username"]

    rv = client.get(url_for("user.view", user=username))
    client.post(
        url_for("do.ban_user", username=username),
        data=dict(csrf_token=csrf_token(rv.data)),
        follow_redirects=True,
    )

    # For now, banning makes you unable to log in.
    log_out_current_user(client)
    log_in_user(client, user_info, expect_success=False)
    log_in_user(client, user2_info)

    rv = client.get(url_for("user.view", user=username))
    client.post(
        url_for("do.unban_user", username=username),
        data=dict(csrf_token=csrf_token(rv.data)),
        follow_redirects=True,
    )

    log_out_current_user(client)
    log_in_user(client, user_info)


@pytest.mark.parametrize("test_config", [{"auth": {"require_valid_emails": True}}])
def test_admin_can_ban_email_domain(client, user_info, test_config):
    register_user(client, user_info)
    promote_user_to_admin(client, user_info)

    rv = client.get(url_for("admin.domains", domain_type="email"))
    rv = client.post(
        url_for("do.ban_domain", domain_type="email"),
        data=dict(csrf_token=csrf_token(rv.data), domain="spam4u.com"),
        follow_redirects=True,
    )
    reply = json.loads(rv.data.decode("utf-8"))
    assert reply["status"] == "ok"

    log_out_current_user(client)
    rv = client.get(url_for("auth.register"))
    with mail.record_messages() as outbox:
        data = dict(
            csrf_token=csrf_token(rv.data),
            username="troll",
            password="Safe123#$@lolnot",
            confirm="Safe123#$@lolnot",
            email_required="troll@spam4u.com",
            invitecode="",
            accept_tos=True,
            captcha="xyzzy",
        )
        rv = client.post(url_for("auth.register"), data=data, follow_redirects=True)
        assert len(outbox) == 0
        assert b"do not accept emails" in rv.data
        assert b"Register" in rv.data
        assert b"Log out" not in rv.data


@pytest.fixture
def null_user() -> User:
    return User.create(
        uid="dummy-user",
        name="abc",
        crypto=0,
    )


@pytest.fixture
def a_sub(app) -> Sub:
    return Sub.create(name="someSub")


@pytest.fixture
def a_post(a_sub, null_user):
    return SubPost.create(
        sid=a_sub,
        title="A new post.",
        comments=0,  # Required for some reason.
        uid=null_user,
    )


@pytest.fixture
def an_announced_post(a_post):
    SiteMetadata.create(key="announcement", value=a_post.pid)
    return a_post


def test_admin_can_make_announcement(client, user2_info, a_post):
    # Given an existing post (a_post).
    # And a logged-in admin user.
    register_user(client, user2_info)
    promote_user_to_admin(client, user2_info)

    # When the admin marks the post as an announcement.
    post_page_response = client.get(
        url_for("sub.view_post", sub=a_post.sid.name, pid=a_post.pid),
        follow_redirects=True,
    )
    csrf = csrf_token(post_page_response.data)
    response = client.post(
        url_for("do.make_announcement"), data={"csrf_token": csrf, "post": a_post.pid}
    )

    # Then the request succeeds.
    assert response.status == "200 OK"
    json_response = json.loads(response.data.decode("utf-8"))
    assert json_response["status"] == "ok", json_response
    # And the ID of the post is stored as the announcement post ID.
    assert int(getAnnouncementPid().value) == a_post.pid


def test_admin_can_delete_announcement(client, user2_info, an_announced_post):
    # Given an announced post. (This is a sanity check.)
    assert int(getAnnouncementPid().value) == an_announced_post.pid
    # And a logged-in admin.
    register_user(client, user2_info)
    promote_user_to_admin(client, user2_info)

    # When the admin deletes the announced post with a GET request.
    client.get(url_for("do.deleteannouncement"))

    # Then attempting to get the announcement post ID raises an exception.
    with pytest.raises(SiteMetadata.DoesNotExist):
        getAnnouncementPid()
