from flask.globals import session
from app import misc
from app.models import InviteCode, SiteMetadata, SubPost, User
import json
import pytest

from flask import url_for

from app import mail
from app.misc import getAnnouncementPid
from app.config import config

from test.factories import AnnouncedPostFactory, PostFactory
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


def http_status_ok(response) -> bool:
    """Test if response HTTP status was 200 OK."""
    return response.status == "200 OK"


def parse_json_response_body(response) -> dict:
    return json.loads(response.data.decode("utf-8"))


def check_json_status(response, expected_status: str) -> bool:
    """Check the status field in the JSON contains the expected string."""
    json_data = parse_json_response_body(response)
    return json_data["status"] == expected_status


def check_json_errors(response, *expected_error_messages: str) -> bool:
    """Check that the expected error messages appear in the JSON."""
    json_data = parse_json_response_body(response)
    expected_errors = set(expected_error_messages)

    error_data = json_data["error"]
    if isinstance(error_data, list):
        received_errors = set(error_data)
    elif isinstance(error_data, str):
        received_errors = {error_data}
    else:
        raise ValueError(f"Unexpected type for 'error': {type(error_data)}.")

    return expected_errors.issubset(received_errors)


def json_status_ok(response) -> bool:
    """Test if the JSON body in the response has a status of 'ok'."""
    return check_json_status(response, "ok")


def json_status_error(response, *expected_errors: str) -> bool:
    """Test if the JSON body in the response has a status of 'error'."""
    return check_json_status(response, "error") and check_json_errors(
        response, *expected_errors
    )


def current_announcement_pid() -> int:
    """Get the pid of the currently announced post as an integer."""
    return int(getAnnouncementPid().value)


def test_admin_can_make_announcement(client, an_admin, csrf_token):
    # Given an existing post and a logged-in admin user.
    a_post: SubPost = PostFactory.create()

    # When the admin marks the post as an announcement.
    announcement_response = client.post(
        url_for("do.make_announcement"),
        data={"csrf_token": csrf_token, "post": a_post.pid},
    )

    # Then the request succeeds.
    assert http_status_ok(announcement_response)
    assert json_status_ok(announcement_response), session
    # And the ID of the post is stored as the announcement post ID.
    assert current_announcement_pid() == a_post.pid


def test_normal_user_cant_access_make_announcement_route(client, a_user) -> None:
    response = client.post(url_for("do.make_announcement"))
    assert response.status_code == 403


def test_anonymous_users_are_redirected_from_make_announcement_route(client) -> None:
    """Ensure that only logged-in users trigger the view at all."""
    response = client.post(url_for("do.make_announcement"))
    assert response.status_code == 302
    assert response.headers["location"].startswith(url_for("auth.login"))


def test_announcing_an_announcement_gives_an_error_response(
    client, an_admin, csrf_token
) -> None:
    # Given an existing announcement and a logged-in admin user.
    announced_post: SubPost = AnnouncedPostFactory.create()

    # When the admin marks the announced post as an announcement.
    announcement_response = client.post(
        url_for("do.make_announcement"),
        data={"csrf_token": csrf_token, "post": announced_post.pid},
    )

    # Then the request returns HTTP 200 but the JSON response notes an error.
    assert http_status_ok(announcement_response)
    assert json_status_error(announcement_response, "Post already announced")
    # And the announced post is unchanged.
    assert current_announcement_pid() == announced_post.pid


def test_announcing_a_post_replaces_an_existing_announcement(
    client, an_admin, csrf_token
) -> None:
    # Given an existing post marked as an announcement.
    existing_announcement: SubPost = AnnouncedPostFactory.create()
    # Sanity check.
    assert current_announcement_pid() == existing_announcement.pid
    # And a new post.
    new_post: SubPost = PostFactory.create()

    # When the admin marks the new post as an announcement.
    announcement_response = client.post(
        url_for("do.make_announcement"),
        data={"csrf_token": csrf_token, "post": new_post.pid},
    )

    # Then the request succeeds.
    assert http_status_ok(announcement_response)
    assert json_status_ok(announcement_response)
    # And the announced post is unchanged.
    assert current_announcement_pid() == new_post.pid


def test_announcing_a_nonexistent_post_gives_an_error_response(
    client, an_admin, csrf_token
) -> None:
    # Given there is no announced post.
    with pytest.raises(SiteMetadata.DoesNotExist):
        current_announcement_pid()

    # When the admin marks the non-existent post as an announcement.
    announcement_response = client.post(
        url_for("do.make_announcement"),
        data={"csrf_token": csrf_token, "post": 42},
    )

    # Then the request returns HTTP 200 but the JSON response notes an error.
    assert http_status_ok(announcement_response)
    assert json_status_error(announcement_response, "Post does not exist")

    # And there remains no announced post.
    with pytest.raises(SiteMetadata.DoesNotExist):
        current_announcement_pid()


def test_make_announcement_gives_error_response_for_invalid_form(
    client, an_admin, csrf_token
) -> None:
    # Given there is no announced post.
    with pytest.raises(SiteMetadata.DoesNotExist):
        current_announcement_pid()

    # When the admin submits an invalid form.
    announcement_response = client.post(
        url_for("do.make_announcement"),
        data={"csrf_token": csrf_token, "post": None},
    )

    # Then the request returns HTTP 200 but the JSON response notes an error.
    assert http_status_ok(announcement_response)
    assert json_status_error(announcement_response)

    # And there remains no announced post.
    with pytest.raises(SiteMetadata.DoesNotExist):
        current_announcement_pid()


def test_delete_announcement_redirects_if_there_is_no_announcement(
    client, an_admin, csrf_token
) -> None:
    response = client.post(
        url_for("do.deleteannouncement"), data={"csrf_token": csrf_token}
    )
    assert response.status_code == 302
    assert response.headers["location"] == url_for("admin.index")


def test_normal_user_cant_access_delete_announcement_route(
    client, a_user, csrf_token
) -> None:
    response = client.post(
        url_for("do.deleteannouncement"), data={"csrf_token": csrf_token}
    )
    assert response.status_code == 403


def number_of_invite_codes_created_by_user(user: User) -> int:
    created = InviteCode.select().where(InviteCode.user == user.uid).count()  # type: ignore
    return created


def available_invite_codes_for_user(user: User) -> int:
    created = number_of_invite_codes_created_by_user(user)
    maxcodes = int(misc.getMaxCodes(user.uid))
    return maxcodes - created


def user_has_invite_codes_remaining(user: User) -> bool:
    return available_invite_codes_for_user(user) > 0


def user_level(user: User) -> int:
    level, _ = misc.get_user_level(user.uid)
    return level


class TestCloseCSRFHole:
    # TODO: 2283:@do.route("/do/create_invite")

    def test_admin_can_delete_announcement(self, client, an_admin, csrf_token):
        # Given a logged-in admin user.
        # And an announced post.
        announced_post: SubPost = AnnouncedPostFactory.create()
        # (This is a sanity check.)
        assert current_announcement_pid() == announced_post.pid

        # When the admin deletes the announced post with a POST request.
        response = client.post(
            url_for("do.deleteannouncement"), data={"csrf_token": csrf_token}
        )

        # Then attempting to get the announcement post ID raises an exception.
        with pytest.raises(SiteMetadata.DoesNotExist):
            current_announcement_pid()
        # And the response redirects to the admin index.
        assert response == 302
        assert response.location == url_for("admin.index")

    def test_delete_announcement_fails_without_csrf_token(self, client, an_admin):
        # Given a logged-in admin user.
        # And an announced post.
        announced_post: SubPost = AnnouncedPostFactory.create()
        # (This is a sanity check.)
        assert current_announcement_pid() == announced_post.pid

        # When the admin attempts to delete the announced post.
        response = client.post(url_for("do.deleteannouncement"))

        # The announced post does not change.
        assert current_announcement_pid() == announced_post.pid
        # And the response indicates a bad request.
        assert response == 400

    def test_delete_announcement_rejects_get_request(self, client, an_admin):
        # Given a logged-in admin user.
        # And an announced post.
        _ = AnnouncedPostFactory.create()

        # When the admin attempts to delete the announced post via GET.
        response = client.get(url_for("do.deleteannouncement"))

        # Then the response indicates the GET method is disallowed.
        assert response == 405

    @pytest.mark.parametrize(
        "view_name",
        [
            "do.enable_captchas",
            "do.enable_registration",
            "do.enable_posting",
        ],
    )
    def test_admin_config_toggle_routes_redirects_anonymous_users(
        self, view_name: str, client, csrf_token
    ) -> None:
        response = client.post(
            url_for(view_name), data={"csrf_token": csrf_token, "value": "True"}
        )
        assert response.status_code == 302
        assert response.headers["location"].startswith(url_for("auth.login"))

    @pytest.mark.parametrize(
        "view_name",
        [
            "do.enable_captchas",
            "do.enable_registration",
            "do.enable_posting",
        ],
    )
    def test_admin_config_toggle_routes_deny_normal_users(
        self, view_name: str, client, a_user, csrf_token
    ) -> None:
        response = client.post(
            url_for(view_name), data={"csrf_token": csrf_token, "value": "True"}
        )
        # Check for 404 not found here for characterisation,
        # but it should perhaps be 403 forbidden.
        assert response.status_code == 404

    @pytest.mark.parametrize(
        "view_name",
        [
            "do.enable_captchas",
            "do.enable_registration",
            "do.enable_posting",
        ],
    )
    @pytest.mark.parametrize(
        "invalid_value",
        [
            "None",
            "on",
            "off",
            "yes",
            "no",
            "1",
            "0",
        ],
    )
    def test_admin_config_toggle_routes_reject_invalid_values(
        self, view_name: str, invalid_value: str, client, an_admin, csrf_token
    ) -> None:
        response = client.post(
            url_for(view_name), data={"csrf_token": csrf_token, "value": invalid_value}
        )
        assert response.status_code == 400, response.location

    @pytest.mark.parametrize(
        "view_name,config_key",
        [
            ("do.enable_captchas", "site.require_captchas"),
            ("do.enable_registration", "site.enable_registration"),
            ("do.enable_posting", "site.enable_posting"),
        ],
    )
    @pytest.mark.parametrize("value", [True, False])
    def test_admin_config_toggle_routes_set_expected_values(
        self, view_name: str, config_key: str, value: bool, client, an_admin, csrf_token
    ) -> None:
        # Given a logged-in admin.
        # When the admin hits the URL.
        response = client.post(
            url_for(view_name), data={"csrf_token": csrf_token, "value": value}
        )

        # Then the config contains the expected value.
        assert config.get_value(config_key) == value
        # And the response redirects the user to the admin index.
        assert response.status_code == 302
        assert response.location == url_for("admin.index")


class TestCreateInvitePost:
    @pytest.mark.parametrize(
        "test_config", [{"site": {"require_invite_code": True, "invite_level": 0}}]
    )
    def test_create_invite_code_successfully(self, client, a_user, csrf_token):
        # Given that invite codes are required.
        # And the user has created no codes.
        assert number_of_invite_codes_created_by_user(a_user) == 0
        # And the user can create more codes.
        assert user_has_invite_codes_remaining(a_user)

        # When the user attempts to create a code.
        response = client.post(
            url_for("do.invite_codes"), data={"csrf_token": csrf_token}
        )

        # Then a new invite code is created.
        assert number_of_invite_codes_created_by_user(a_user) == 1
        # And the user is redirected to the invite settings page.
        assert response == 302
        assert response.location.startswith(url_for("user.invite_codes"))

    @pytest.mark.parametrize(
        "test_config", [{"site": {"require_invite_code": True, "invite_level": 0}}]
    )
    def test_create_invite_code_rejects_requests_without_csrf_token(
        self, client, a_user
    ):
        # Given that invite codes are required.
        # And the user has created no codes.
        assert number_of_invite_codes_created_by_user(a_user) == 0
        # And the user can create more codes.
        assert user_has_invite_codes_remaining(a_user)

        # When the user attempts to create a code.
        response = client.post(
            url_for("do.invite_codes"), data={"csrf_token": csrf_token}
        )

        # Then no new invite code is created.
        assert number_of_invite_codes_created_by_user(a_user) == 0
        # And the response is a 400 error.
        assert response == 400

    @pytest.mark.parametrize("test_config", [{"site": {"require_invite_code": False}}])
    def test_create_invite_redirects_to_settings_when_invites_are_disabled(
        self, client, a_user, csrf_token
    ) -> None:
        # Given invite codes are not required.
        # When the user attempts to create a code.
        response = client.post(
            url_for("do.invite_codes"), data={"csrf_token": csrf_token}
        )
        # Then they are directed to their settings page.
        assert response == 302
        assert response.location.startswith(url_for("user.edit_user"))

    def test_create_invite_redirects_anonymous_users_to_login(
        self, client, csrf_token
    ) -> None:
        # Given the user is not logged in.
        # When they attempt to create an invite code.
        response = client.post(
            url_for("do.invite_codes"), data={"csrf_token": csrf_token}
        )
        # They are redirected to the login page.
        assert response == 302
        assert response.location.startswith(url_for("auth.login"))

    @pytest.mark.parametrize(
        "test_config", [{"site": {"require_invite_code": True, "invite_level": 1}}]
    )
    def test_create_invite_code_fails_when_level_is_too_low(
        self, client, a_user, csrf_token
    ):
        # Given that invite codes are required.
        # And the user has too low a level to create codes.
        assert config.site.invite_level > user_level(a_user)

        # When the user attempts to create a code.
        response = client.post(
            url_for("do.invite_codes"), data={"csrf_token": csrf_token}
        )

        # Then no invite code is created.
        assert number_of_invite_codes_created_by_user(a_user) == 0
        # And the user is redirected to the invite settings page.
        assert response.status_code == 302
        assert response.headers["location"].startswith(url_for("user.invite_codes"))
