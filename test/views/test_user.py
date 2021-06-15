from app.config import config
from app.models import User
from flask import url_for
from test.utilities import (
    number_of_invite_codes_created_by_user,
    register_user,
    user_has_invite_codes_remaining,
    user_level,
)

import pytest


def test_settings_page(client, user_info):
    register_user(client, user_info)
    username = user_info["username"]
    assert client.get(url_for("user.edit_user", user=username)).status_code == 200


@pytest.mark.parametrize(
    "test_config", [{"site": {"require_invite_code": True, "invite_level": 0}}]
)
def test_create_invite_code_successfully(client, a_user: User, csrf_token: str) -> None:
    # Given that invite codes are required.
    # And the user has created no codes.
    assert number_of_invite_codes_created_by_user(a_user) == 0
    # And the user can create more codes.
    assert user_has_invite_codes_remaining(a_user)

    # When the user attempts to create a code.
    response = client.post(url_for("do.invite_codes"), data={"csrf_token": csrf_token})

    # Then a new invite code is created.
    assert number_of_invite_codes_created_by_user(a_user) == 1
    # And the user is redirected to the invite settings page.
    assert response == 302
    assert response.location.startswith(url_for("user.invite_codes"))


@pytest.mark.parametrize(
    "test_config", [{"site": {"require_invite_code": True, "invite_level": 0}}]
)
def test_create_invite_code_rejects_requests_without_csrf_token(
    client, a_user: User
) -> None:
    # Given that invite codes are required.
    # And the user has created no codes.
    assert number_of_invite_codes_created_by_user(a_user) == 0
    # And the user can create more codes.
    assert user_has_invite_codes_remaining(a_user)

    # When the user attempts to create a code.
    response = client.post(url_for("do.invite_codes"), data={"csrf_token": ""})

    # Then no new invite code is created.
    assert number_of_invite_codes_created_by_user(a_user) == 0
    # And the response is a 400 error.
    assert response == 400


@pytest.mark.parametrize("test_config", [{"site": {"require_invite_code": False}}])
def test_create_invite_redirects_to_settings_when_invites_are_disabled(
    client, a_user: User, csrf_token: str
) -> None:
    # Given invite codes are not required.
    # When the user attempts to create a code.
    response = client.post(url_for("do.invite_codes"), data={"csrf_token": csrf_token})
    # Then they are directed to their settings page.
    assert response == 302
    assert response.location.startswith(url_for("user.edit_user"))


def test_create_invite_redirects_anonymous_users_to_login(
    client, csrf_token: str
) -> None:
    # Given the user is not logged in.
    # When they attempt to create an invite code.
    response = client.post(url_for("do.invite_codes"), data={"csrf_token": csrf_token})
    # They are redirected to the login page.
    assert response == 302
    assert response.location.startswith(url_for("auth.login"))


@pytest.mark.parametrize(
    "test_config", [{"site": {"require_invite_code": True, "invite_level": 1}}]
)
def test_create_invite_code_fails_when_level_is_too_low(
    client, a_user: User, csrf_token: str
) -> None:
    # Given that invite codes are required.
    # And the user has too low a level to create codes.
    assert config.site.invite_level > user_level(a_user)

    # When the user attempts to create a code.
    response = client.post(url_for("do.invite_codes"), data={"csrf_token": csrf_token})

    # Then no invite code is created.
    assert number_of_invite_codes_created_by_user(a_user) == 0
    # And the user is redirected to the invite settings page.
    assert response.status_code == 302
    assert response.headers["location"].startswith(url_for("user.invite_codes"))
