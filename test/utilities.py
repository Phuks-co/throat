from bs4 import BeautifulSoup
from flask import url_for
import json
from peewee import fn

from app import mail, misc
from app.auth import email_validation_is_required
from app.models import InviteCode, User, UserMetadata, SiteMetadata


def csrf_token(data):
    soup = BeautifulSoup(data, "html.parser")
    # print(soup.prettify())
    return soup.find(id="csrf_token")["value"]


def get_value(data, key):
    soup = BeautifulSoup(data, "html.parser")
    # print(soup.prettify())
    return soup.find(id=key)["value"]


# pretty-print for debugging purposes
def pp(data):
    print(BeautifulSoup(data, "html.parser").prettify())


def recursively_update(dictionary, new_values):
    for elem in new_values.keys():
        if (
            elem in dictionary.keys()
            and isinstance(new_values[elem], dict)
            and isinstance(dictionary[elem], dict)
        ):
            recursively_update(dictionary[elem], new_values[elem])
        else:
            dictionary[elem] = new_values[elem]


def add_config_to_site_metadata(config):
    """Add config values to the database."""

    def get_value(value, typ):
        if typ == "bool":
            return "1" if value else "0"
        else:
            return str(value)

    new_records = [
        {"key": key, "value": get_value(val, typ)}
        for key, val, typ in config.mutable_item_configuration()
    ]
    SiteMetadata.insert_many(new_records).execute()


def log_in_user(client, user_info, expect_success=True):
    """Log in the user described by the user_info directory.  User should
    already be registered."""
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
    if expect_success:
        assert b"Log out" in rv.data
    else:
        assert b"Log in" in rv.data


def log_out_current_user(client, verify=True):
    """Log out the user who is logged in."""
    rv = client.get(url_for("home.index"))
    rv = client.post(
        url_for("do.logout"),
        data=dict(csrf_token=csrf_token(rv.data)),
        follow_redirects=True,
    )
    if verify:
        assert b"Log in" in rv.data


def register_user(client, user_info):
    """Register a user with the client and leave them logged in."""
    rv = client.get(url_for("home.index"))
    client.post(
        url_for("do.logout"),
        data=dict(csrf_token=csrf_token(rv.data)),
        follow_redirects=True,
    )
    rv = client.get(url_for("auth.register"))
    with mail.record_messages() as outbox:
        data = dict(
            csrf_token=csrf_token(rv.data),
            username=user_info["username"],
            password=user_info["password"],
            confirm=user_info["password"],
            invitecode="",
            accept_tos=True,
            captcha="xyzzy",
        )
        if email_validation_is_required():
            data["email_required"] = user_info["email"]
        else:
            data["email_optional"] = user_info["email"]

        client.post(url_for("auth.register"), data=data, follow_redirects=True)

        if email_validation_is_required():
            message = outbox[-1]
            soup = BeautifulSoup(message.html, "html.parser")
            token = soup.a["href"].split("/")[-1]
            client.get(
                url_for("auth.login_with_token", token=token), follow_redirects=True
            )


def create_sub(client, allow_polls=False):
    rv = client.get(url_for("subs.create_sub"))
    assert rv.status_code == 200

    data = {"csrf_token": csrf_token(rv.data), "subname": "test", "title": "Testing"}

    rv = client.post(url_for("subs.create_sub"), data=data, follow_redirects=True)
    assert b"/s/test" in rv.data


def promote_user_to_admin(client, user_info):
    """Assuming user_info is the info for the logged-in user, promote them
    to admin and leave them logged in.
    """
    log_out_current_user(client)
    admin = User.get(fn.Lower(User.name) == user_info["username"])
    UserMetadata.create(uid=admin.uid, key="admin", value="1")
    log_in_user(client, user_info)


def force_log_in(user: User, client) -> None:
    with client.session_transaction() as session:
        session["_user_id"] = user.uid


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
    return int(misc.getAnnouncementPid().value)
