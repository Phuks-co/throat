import pytest
from datetime import timedelta
import json
from bs4 import BeautifulSoup
from flask import url_for

from app import mail
from app.auth import email_validation_is_required, auth_provider
from app.models import UserStatus, User

from test.utilities import csrf_token, get_value
from test.utilities import register_user, log_in_user, log_out_current_user
from test.utilities import promote_user_to_admin


@pytest.mark.parametrize(
    "test_config",
    [{"auth": {"require_valid_emails": False}}],
)
def test_registration_login(client, test_config):
    """The registration page logs a user in if they register correctly."""
    rv = client.get(url_for("auth.register"))
    with mail.record_messages() as outbox:
        data = dict(
            csrf_token=csrf_token(rv.data),
            username="supertester",
            password="Safe123#$@lolnot",
            confirm="Safe123#$@lolnot",
            invitecode="",
            accept_tos=True,
            captcha="xyzzy",
        )
        if email_validation_is_required():
            data["email_required"] = "test@example.com"
        else:
            data["email_optional"] = "test@example.com"
        rv = client.post(url_for("auth.register"), data=data, follow_redirects=True)

        if email_validation_is_required():
            assert b"spam" in rv.data  # Telling user to go check it.
            message = outbox[-1]
            soup = BeautifulSoup(message.html, "html.parser", from_encoding="utf-8")
            token = soup.a["href"].split("/")[-1]
            rv = client.get(
                url_for("auth.login_with_token", token=token), follow_redirects=True
            )

        assert auth_provider.get_user_by_email("test@example.com").name == "supertester"
        assert b"Log out" in rv.data


@pytest.mark.parametrize("test_config", [{"auth": {"require_valid_emails": True}}])
def test_email_required_for_registration(client, user_info, test_config):
    """
    If emails are required, trying to register without one will fail.
    """
    rv = client.get(url_for("auth.register"))
    with mail.record_messages() as outbox:
        data = dict(
            csrf_token=csrf_token(rv.data),
            username="supertester",
            password="Safe123#$@lolnot",
            confirm="Safe123#$@lolnot",
            email_required="",
            invitecode="",
            accept_tos=True,
            captcha="xyzzy",
        )
        rv = client.post(url_for("auth.register"), data=data, follow_redirects=True)
        assert len(outbox) == 0
        assert b"Error" in rv.data
        assert b"Register" in rv.data
        assert b"Log out" not in rv.data


@pytest.mark.parametrize("test_config", [{"auth": {"require_valid_emails": True}}])
def test_login_before_confirming_email(client, user_info, test_config):
    """Registered users with unconfirmed emails can't log in."""
    rv = client.get(url_for("auth.register"))
    with mail.record_messages() as outbox:
        data = dict(
            csrf_token=csrf_token(rv.data),
            username=user_info["username"],
            password=user_info["password"],
            confirm=user_info["password"],
            email_required=user_info["email"],
            invitecode="",
            accept_tos=True,
            captcha="xyzzy",
        )
        rv = client.post(url_for("auth.register"), data=data, follow_redirects=True)
        assert b"spam" in rv.data  # Telling user to go check it.

        message = outbox.pop()

        rv = client.get(url_for("auth.login"))
        rv = client.post(
            url_for("auth.login"),
            data=dict(
                csrf_token=csrf_token(rv.data),
                username=user_info["username"],
                password=user_info["password"],
            ),
            follow_redirects=True,
        )
        assert b"Resend account confirmation instructions" in rv.data
        rv = client.post(
            url_for("auth.resend_confirmation_email"),
            data=dict(csrf_token=csrf_token(rv.data), email=user_info["email"]),
            follow_redirects=True,
        )

        assert b"spam" in rv.data  # Telling user to go check it.
        message = outbox.pop()
        soup = BeautifulSoup(message.html, "html.parser")
        token = soup.a["href"].split("/")[-1]
        rv = client.get(
            url_for("auth.login_with_token", token=token), follow_redirects=True
        )

        assert b"Log out" in rv.data


@pytest.mark.parametrize("test_config", [{"auth": {"require_valid_emails": True}}])
def test_resend_registration_email(client, user_info, test_config):
    """Registered but unconfirmed users can resend the registration link."""
    rv = client.get(url_for("auth.register"))
    data = dict(
        csrf_token=csrf_token(rv.data),
        username=user_info["username"],
        password=user_info["password"],
        confirm=user_info["password"],
        email_required=user_info["email"],
        invitecode="",
        accept_tos=True,
        captcha="xyzzy",
    )

    rv = client.post(url_for("auth.register"), data=data, follow_redirects=True)
    assert b"spam" in rv.data  # Telling user to go check it.

    # Find the resend link.
    soup = BeautifulSoup(rv.data, "html.parser", from_encoding="utf-8")
    links = soup.find_all(lambda tag: tag.name == "a" and tag.string == "Resend")
    url = links[0]["href"]

    # Request the resend form and verify the registered email is shown.
    rv = client.get(url)
    assert b"Resend account confirmation instructions" in rv.data
    soup = BeautifulSoup(rv.data, "html.parser", from_encoding="utf-8")
    tag = soup.find_all(lambda tag: tag.get("name") == "email")[0]
    assert tag["value"] == user_info["email"]

    # Use the resend form and the resent link.
    with mail.record_messages() as outbox:
        rv = client.post(
            url,
            data=dict(
                csrf_token=csrf_token(rv.data),
                email=user_info["email"],
            ),
            follow_redirects=True,
        )
        assert b"spam" in rv.data  # Telling user to go check it.
        message = outbox.pop()
        soup = BeautifulSoup(message.html, "html.parser")
        token = soup.a["href"].split("/")[-1]
        rv = client.get(
            url_for("auth.login_with_token", token=token), follow_redirects=True
        )
        assert b"Log out" in rv.data


@pytest.mark.parametrize("test_config", [{"auth": {"require_valid_emails": True}}])
def test_resend_registration_email_after_confirmation(client, user_info, test_config):
    """Registration instructions cannot be resent after confirmation."""
    with mail.record_messages() as outbox:
        rv = client.get(url_for("auth.register"))
        data = dict(
            csrf_token=csrf_token(rv.data),
            username=user_info["username"],
            password=user_info["password"],
            confirm=user_info["password"],
            email_required=user_info["email"],
            invitecode="",
            accept_tos=True,
            captcha="xyzzy",
        )
        rv = client.post(url_for("auth.register"), data=data, follow_redirects=True)
        assert b"spam" in rv.data  # Telling user to go check it.

        # Find the resend link.
        soup = BeautifulSoup(rv.data, "html.parser", from_encoding="utf-8")
        link = soup.find_all(lambda tag: tag.name == "a" and tag.string == "Resend")[0]
        url = link["href"]

        # Find and use the confirmation link.
        message = outbox[-1]
        soup = BeautifulSoup(message.html, "html.parser")
        token = soup.a["href"].split("/")[-1]
        rv = client.get(
            url_for("auth.login_with_token", token=token), follow_redirects=True
        )

    assert b"Log out" in rv.data
    log_out_current_user(client, verify=True)

    # Request the resend form and verify an error message is shown.
    rv = client.get(url, follow_redirects=True)
    assert b"The link you used is invalid or has expired" in rv.data
    assert b"Log out" not in rv.data


@pytest.mark.parametrize("test_config", [{"auth": {"require_valid_emails": True}}])
def test_fix_registration_email(client, user_info, user2_info, test_config):
    """Registered users can fix errors in their email addresses."""
    rv = client.get(url_for("auth.register"))
    data = dict(
        csrf_token=csrf_token(rv.data),
        username=user_info["username"],
        password=user_info["password"],
        confirm=user_info["password"],
        email_required=user_info["email"],
        invitecode="",
        accept_tos=True,
        captcha="xyzzy",
    )

    # Register and save the link from the first email.
    with mail.record_messages() as outbox:
        rv = client.post(url_for("auth.register"), data=data, follow_redirects=True)
        assert b"spam" in rv.data  # Telling user to go check it.
        message = outbox.pop()
        soup = BeautifulSoup(message.html, "html.parser")
        first_token = soup.a["href"].split("/")[-1]

    # Find the resend link.
    soup = BeautifulSoup(rv.data, "html.parser", from_encoding="utf-8")
    links = soup.find_all(lambda tag: tag.name == "a" and tag.string == "Resend")
    url = links[0]["href"]

    # Request the resend form and verify the registered email is shown.
    rv = client.get(url)
    assert b"Resend account confirmation instructions" in rv.data
    soup = BeautifulSoup(rv.data, "html.parser", from_encoding="utf-8")
    tag = soup.find_all(lambda tag: tag.get("name") == "email")[0]
    assert tag["value"] == user_info["email"]

    # Ask for emails to be sent to a different address.
    with mail.record_messages() as outbox:
        rv = client.post(
            url,
            data=dict(csrf_token=csrf_token(rv.data), email=user2_info["email"]),
            follow_redirects=True,
        )
        assert b"spam" in rv.data  # Telling user to go check it.
        message = outbox.pop()
        assert message.recipients == [user2_info["email"]]
        soup = BeautifulSoup(message.html, "html.parser")
        token = soup.a["href"].split("/")[-1]

        # Use the confirmation link from the email.
        rv = client.get(
            url_for("auth.login_with_token", token=token), follow_redirects=True
        )
        assert b"Log out" in rv.data

    # Verify that the user's confirmed email is the second one.
    rv = client.get(url_for("user.edit_account"))
    soup = BeautifulSoup(rv.data, "html.parser", from_encoding="utf-8")
    tag = soup.find_all(lambda tag: tag.get("name") == "email_required")[0]
    assert tag["value"] == user2_info["email"]

    log_out_current_user(client)

    # Try to use the first token and verify that it is no longer valid.
    rv = client.get(
        url_for("auth.login_with_token", token=first_token), follow_redirects=True
    )
    assert b"The link you used is invalid or has expired" in rv.data
    assert b"Log out" not in rv.data

    # Try to use the resend form and verify that it no longer works.
    rv = client.get(url, follow_redirects=True)
    assert b"The link you used is invalid or has expired" in rv.data
    assert b"Log out" not in rv.data


def test_logout_and_login_again(client, user_info):
    """A logged in user can log out and back in again."""
    register_user(client, user_info)
    assert b"Log out" in client.get(url_for("home.index")).data
    log_out_current_user(client, verify=True)
    log_in_user(client, user_info, expect_success=True)


def test_change_password(client, user_info):
    """A user can change their password and log in with the new password."""
    register_user(client, user_info)
    new_password = "mynewSuperSecret#123" + "\N{PARTIAL DIFFERENTIAL}"
    assert new_password != user_info["password"]
    rv = client.get(url_for("user.edit_account"))
    rv = client.post(
        url_for("do.edit_account"),
        data=dict(
            csrf_token=csrf_token(rv.data),
            oldpassword=user_info["password"],
            password=new_password,
            confirm=new_password,
            email="",
        ),
        follow_redirects=True,
    )
    reply = json.loads(rv.data.decode("utf-8"))
    print(reply)
    assert reply["status"] == "ok"

    log_out_current_user(client)

    # Try to log in with the old password
    log_in_user(client, user_info, expect_success=False)

    new_info = dict(user_info)
    new_info.update(password=new_password)
    log_in_user(client, new_info, expect_success=True)


@pytest.mark.parametrize(
    "test_config",
    [
        {"auth": {"require_valid_emails": True}},
        {"auth": {"require_valid_emails": False}},
    ],
)
def test_change_password_recovery_email(client, user_info, test_config):
    """The user can change their password recovery email."""
    register_user(client, user_info)
    new_email = "sock@example.com"
    assert new_email != user_info["email"]

    rv = client.get(url_for("user.edit_account"))
    data = dict(
        csrf_token=csrf_token(rv.data),
        oldpassword=user_info["password"],
        password="",
        confirm="",
    )
    if email_validation_is_required():
        data["email_required"] = new_email
    else:
        data["email_optional"] = new_email

    with mail.record_messages() as outbox:
        rv = client.post(url_for("do.edit_account"), data=data, follow_redirects=True)
        log_out_current_user(client)

        if email_validation_is_required():
            message = outbox.pop()

            # Make sure that password recovery emails go to the former address
            # if the new one has not yet been confirmed.
            rv = client.get(url_for("user.password_recovery"))
            rv = client.post(
                url_for("user.password_recovery"),
                data=dict(
                    csrf_token=csrf_token(rv.data), email=new_email, captcha="xyzzy"
                ),
            )
            assert len(outbox) == 0

            rv = client.get(url_for("user.password_recovery"))
            rv = client.post(
                url_for("user.password_recovery"),
                data=dict(
                    csrf_token=csrf_token(rv.data),
                    email=user_info["email"],
                    captcha="xyzzy",
                ),
            )
            assert outbox.pop().send_to == {user_info["email"]}

            # Now click the confirm link.
            assert message.send_to == {new_email}
            soup = BeautifulSoup(message.html, "html.parser")
            token = soup.a["href"].split("/")[-1]
            rv = client.get(
                url_for("user.confirm_email_change", token=token), follow_redirects=True
            )
        else:
            assert len(outbox) == 0

    # Verify password recovery email goes to the right place.
    with mail.record_messages() as outbox:
        rv = client.get(url_for("user.password_recovery"))
        rv = client.post(
            url_for("user.password_recovery"),
            data=dict(
                csrf_token=csrf_token(rv.data),
                email=user_info["email"],
                captcha="xyzzy",
            ),
        )
        assert len(outbox) == 0
        rv = client.get(url_for("user.password_recovery"))
        rv = client.post(
            url_for("user.password_recovery"),
            data=dict(csrf_token=csrf_token(rv.data), email=new_email, captcha="xyzzy"),
        )
        assert outbox.pop().send_to == {new_email}


@pytest.mark.parametrize("test_config", [{"auth": {"require_valid_emails": True}}])
def test_password_required_to_change_recovery_email(client, user_info, test_config):
    """Changing the password recovery requires the correct password."""
    register_user(client, user_info)
    wrong_password = "mynewSuperSecret#123"
    new_email = "sock@example.com"
    assert wrong_password != user_info["password"]
    assert new_email != user_info["email"]

    rv = client.get(url_for("user.edit_account"))
    data = dict(
        csrf_token=csrf_token(rv.data),
        email_required=new_email,
        oldpassword=wrong_password,
        password="",
        confirm="",
    )

    # No confirmation email should be sent.
    with mail.record_messages() as outbox:
        rv = client.post(url_for("do.edit_account"), data=data, follow_redirects=True)
        assert len(outbox) == 0

    log_out_current_user(client)

    # Verify password recovery email goes to the right place.
    with mail.record_messages() as outbox:
        rv = client.get(url_for("user.password_recovery"))
        rv = client.post(
            url_for("user.password_recovery"),
            data=dict(csrf_token=csrf_token(rv.data), email=new_email, captcha="xyzzy"),
        )
        assert len(outbox) == 0
        rv = client.get(url_for("user.password_recovery"))
        rv = client.post(
            url_for("user.password_recovery"),
            data=dict(
                csrf_token=csrf_token(rv.data),
                email=user_info["email"],
                captcha="xyzzy",
            ),
        )
        assert len(outbox) == 1


def test_reset_password(client, user_info):
    """A user can reset their password using a link sent to their email."""
    new_password = "New_Password123"
    assert new_password != user_info["password"]
    register_user(client, user_info)
    log_out_current_user(client)

    with mail.record_messages() as outbox:
        rv = client.get(url_for("user.password_recovery"))
        rv = client.post(
            url_for("user.password_recovery"),
            data=dict(
                csrf_token=csrf_token(rv.data),
                email=user_info["email"],
                captcha="xyzzy",
            ),
        )
        message = outbox.pop()
        assert message.send_to == {user_info["email"]}
        soup = BeautifulSoup(message.html, "html.parser")
        token = soup.a["href"].split("/")[-1]
        rv = client.get(
            url_for("user.password_reset", token=token), follow_redirects=True
        )
        rv = client.post(
            url_for("do.reset"),
            data=dict(
                csrf_token=csrf_token(rv.data),
                user=get_value(rv.data, "user"),
                key=get_value(rv.data, "key"),
                password=new_password,
                confirm=new_password,
            ),
        )

        log_out_current_user(client)
        user_info["password"] = new_password
        log_in_user(client, user_info, expect_success=True)


# TODO test that you can change email to nada and old email wont' work
# TODO verify that they can't change to an email someone else has
# including one someone else is trying to change to


def test_delete_account(client, user_info):
    """A user can delete their account."""
    register_user(client, user_info)

    # The password has to be right.
    rv = client.get(url_for("user.delete_account"))
    rv = client.post(
        url_for("do.delete_user"),
        data=dict(
            csrf_token=csrf_token(rv.data),
            password="ThisIsNotTheRightPassword",
            consent="YES",
        ),
        follow_redirects=True,
    )
    reply = json.loads(rv.data.decode("utf-8"))
    assert reply["status"] == "error"

    # The consent must be given.
    rv = client.get(url_for("user.delete_account"))
    rv = client.post(
        url_for("do.delete_user"),
        data=dict(
            csrf_token=csrf_token(rv.data),
            password="ThisIsNotTheRightPassword",
            consent="NO",
        ),
        follow_redirects=True,
    )
    reply = json.loads(rv.data.decode("utf-8"))
    assert reply["status"] == "error"

    rv = client.get(url_for("user.delete_account"))
    rv = client.post(
        url_for("do.delete_user"),
        data=dict(
            csrf_token=csrf_token(rv.data),
            password=user_info["password"],
            consent="YES",
        ),
        follow_redirects=True,
    )
    reply = json.loads(rv.data.decode("utf-8"))
    assert reply["status"] == "ok"

    # Deleting your account should log you out.
    rv = client.get(url_for("home.index"))
    assert b"Log in" in rv.data

    # Try to log in to the deleted account.
    log_in_user(client, user_info, expect_success=False)


# TODO deleted users should be able to make a new account with the
# same email but banned users should not


@pytest.mark.parametrize("test_config", [{"auth": {"require_valid_emails": True}}])
def test_reregister(client, user_info, user2_info, test_config):
    "A user account which is unconfirmed after two days can be re-registered."
    rv = client.get(url_for("auth.register"))
    data = dict(
        csrf_token=csrf_token(rv.data),
        username=user_info["username"],
        password=user_info["password"],
        confirm=user_info["password"],
        invitecode="",
        accept_tos=True,
        email_required=user_info["email"],
        captcha="xyzzy",
    )
    client.post(url_for("auth.register"), data=data, follow_redirects=True)

    new_user = User.get(User.name == user_info["username"])
    assert new_user.status == UserStatus.PROBATION
    new_user.joindate -= timedelta(days=3)
    new_user.save()

    rv = client.get(url_for("auth.register"))
    with mail.record_messages() as outbox:
        data = dict(
            csrf_token=csrf_token(rv.data),
            username=user_info["username"],
            password=user_info["password"],
            confirm=user_info["password"],
            invitecode="",
            email_required=user2_info["email"],
            accept_tos=True,
        )
        rv = client.post(url_for("auth.register"), data=data, follow_redirects=True)

        assert b"spam" in rv.data  # Telling user to go check it.
        message = outbox[-1]
        assert message.send_to == {user2_info["email"]}
        soup = BeautifulSoup(message.html, "html.parser")
        token = soup.a["href"].split("/")[-1]
        rv = client.get(
            url_for("auth.login_with_token", token=token), follow_redirects=True
        )
        assert b"Log out" in rv.data

    assert auth_provider.get_user_by_email(user_info["email"]) is None
    assert (
        auth_provider.get_user_by_email(user2_info["email"]).name
        == user_info["username"]
    )


def test_invite_code_required_for_registration(client, user_info, user2_info):
    """If invite codes are required, trying to register without one will fail."""
    register_user(client, user_info)
    promote_user_to_admin(client, user_info)

    # Enable invite codes.
    rv = client.get(url_for("admin.invitecodes"))
    data = dict(
        csrf_token=csrf_token(rv.data), enableinvitecode=True, minlevel=3, maxcodes=10
    )

    rv = client.post(url_for("do.use_invite_code"), data=data, follow_redirects=True)
    reply = json.loads(rv.data.decode("utf-8"))
    assert reply["status"] == "ok"

    # Create an invite code.
    rv = client.get(url_for("admin.invitecodes"))
    data = dict(csrf_token=csrf_token(rv.data), code="abcde", uses=10, expires="")
    client.post(url_for("admin.invitecodes"), data=data, follow_redirects=True)

    log_out_current_user(client)

    # Now try to register a new user without an invite code.
    rv = client.get(url_for("auth.register"))
    data = dict(
        csrf_token=csrf_token(rv.data),
        username=user2_info["username"],
        password=user2_info["password"],
        confirm=user2_info["password"],
        invitecode="",
        email_optional=user2_info["email"],
        accept_tos=True,
        captcha="xyzzy",
    )

    rv = client.post(url_for("auth.register"), data=data, follow_redirects=True)
    assert b"Invalid invite code" in rv.data

    # Now try to register a new user with an incorrect invite code.
    rv = client.get(url_for("auth.register"))
    data = dict(
        csrf_token=csrf_token(rv.data),
        username=user2_info["username"],
        password=user2_info["password"],
        confirm=user2_info["password"],
        invitecode="xyzzy",
        email_optional=user2_info["email"],
        accept_tos=True,
        captcha="xyzzy",
    )

    rv = client.post(url_for("auth.register"), data=data, follow_redirects=True)
    assert b"Invalid invite code" in rv.data

    # Now try to register a new user with a valid invite code.
    rv = client.get(url_for("auth.register"))
    data = dict(
        csrf_token=csrf_token(rv.data),
        username=user2_info["username"],
        password=user2_info["password"],
        confirm=user2_info["password"],
        invitecode="abcde",
        email_optional=user2_info["email"],
        accept_tos=True,
        captcha="xyzzy",
    )

    rv = client.post(url_for("auth.register"), data=data, follow_redirects=True)
    assert b"Log out" in rv.data
