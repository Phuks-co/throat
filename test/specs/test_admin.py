from app.models import SiteMetadata, Sub, SubPost, User
import json
import pytest

from faker import Faker
from flask import g, url_for
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
def a_user(faker: Faker) -> User:
    """Create a bare-bones user."""
    return User.create(
        uid=faker.pystr(),
        name=faker.user_name(),
        crypto=0,
    )


@pytest.fixture
def a_sub(app, faker: Faker) -> Sub:
    """Create a bare-bones sub."""
    return Sub.create(name=faker.word())


@pytest.fixture
def a_post(a_sub: Sub, a_user: User, faker: Faker) -> SubPost:
    """Create a bare-bones post."""
    return SubPost.create(
        sid=a_sub,
        title=faker.sentence(),
        comments=0,  # Required for some reason.
        uid=a_user,
    )


@pytest.fixture
def an_announced_post(a_post: SubPost) -> SubPost:
    """Return a post marked as an announcement."""
    SiteMetadata.create(key="announcement", value=a_post.pid)
    return a_post


@pytest.fixture
def a_logged_in_user(client, user2_info) -> None:
    register_user(client, user2_info)


@pytest.fixture
def a_logged_in_admin(client, user2_info) -> None:
    """Register a new admin user, which is left logged-in."""
    register_user(client, user2_info)
    promote_user_to_admin(client, user2_info)


def http_status_ok(response) -> bool:
    """Test if response HTTP status was 200 OK."""
    return response.status == "200 OK"


def parse_json_response_body(response) -> dict:
    return json.loads(response.data.decode("utf-8"))


def check_json_status(response, expected_status: str) -> bool:
    """Check the status field in the JSON contains the expected string."""
    json_data = parse_json_response_body(response)
    return json_data["status"] == expected_status


def json_status_ok(response) -> bool:
    """Test if the JSON body in the response has a status of 'ok'."""
    return check_json_status(response, "ok")


def json_status_error(response) -> bool:
    """Test if the JSON body in the response has a status of 'error'."""
    return check_json_status(response, "error")


def current_announcement_pid() -> int:
    """Get the pid of the currently announced post as an integer."""
    return int(getAnnouncementPid().value)


def test_admin_can_make_announcement(client, a_logged_in_admin: None, a_post: SubPost):
    # Given an existing post and a logged-in admin user.

    # When the admin marks the post as an announcement.
    announcement_response = client.post(
        url_for("do.make_announcement"),
        data={"csrf_token": g.csrf_token, "post": a_post.pid},
    )

    # Then the request succeeds.
    assert http_status_ok(announcement_response)
    assert json_status_ok(announcement_response)
    # And the ID of the post is stored as the announcement post ID.
    assert current_announcement_pid() == a_post.pid


def test_normal_user_cant_access_make_announcement_route(
    client, a_logged_in_user: None
) -> None:
    response = client.post(url_for("do.make_announcement"))
    assert response.status_code == 403


def test_anonymous_users_are_redirected_from_make_announcement_route(client) -> None:
    """Ensure that only logged-in users trigger the view at all."""
    response = client.post(url_for("do.make_announcement"))
    assert response.status_code == 302
    assert response.headers["location"].startswith(url_for("auth.login"))


def test_announcing_an_announcement_gives_an_error_response(
    client, an_announced_post: SubPost, a_logged_in_admin: None
) -> None:
    # Given an existing announcement and a logged-in admin user.

    # When the admin marks the announced post as an announcement.
    announcement_response = client.post(
        url_for("do.make_announcement"),
        data={"csrf_token": g.csrf_token, "post": an_announced_post.pid},
    )

    # Then the request returns HTTP 200 but the JSON response notes an error.
    assert http_status_ok(announcement_response)
    assert json_status_error(announcement_response)
    # And the announced post is unchanged.
    assert current_announcement_pid() == an_announced_post.pid


def test_admin_can_delete_announcement(
    client, a_logged_in_admin: None, an_announced_post: SubPost
):
    # Given an announced post. (This is a sanity check.)
    assert current_announcement_pid() == an_announced_post.pid
    # And a logged-in admin user.

    # When the admin deletes the announced post with a GET request.
    client.get(url_for("do.deleteannouncement"))

    # Then attempting to get the announcement post ID raises an exception.
    with pytest.raises(SiteMetadata.DoesNotExist):
        current_announcement_pid()


def test_delete_announcement_redirects_if_there_is_no_announcement(
    client, a_logged_in_admin: None
) -> None:
    response = client.get(url_for("do.deleteannouncement"))
    assert response.status_code == 302
    assert response.headers["location"] == url_for("admin.index")


def test_normal_user_cant_access_delete_announcement_route(
    client, a_logged_in_user: None
) -> None:
    response = client.get(url_for("do.deleteannouncement"))
    assert response.status_code == 403
