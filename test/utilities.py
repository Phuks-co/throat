from datetime import datetime, timedelta
import re
from bs4 import BeautifulSoup
from flask import url_for
from peewee import fn
from app import mail
from app.auth import email_validation_is_required
from app.models import User, UserMetadata, SiteMetadata


def csrf_token(data):
    f = re.search(rb'name="csrf_token" type="hidden" value="(.+?)"', data)
    return f.group(1).decode("utf-8")


def get_value(data, key):
    soup = BeautifulSoup(data, "html.parser", from_encoding="utf-8")
    # print(soup.prettify())
    return soup.find(id=key)["value"]


def get_error_text(data):
    soup = BeautifulSoup(data, "html.parser")
    error = soup.find(class_="error")
    return error.get_text() if error is not None else ""


# pretty-print for debugging purposes
def pp(data):
    print(BeautifulSoup(data, "html.parser", from_encoding="utf-8").prettify())


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
    SiteMetadata.create(
        key="best_comment_sort_init",
        value=(datetime.utcnow() - timedelta(seconds=1)).strftime(
            "%Y-%m-%UdT%H:%M:%SZ"
        ),
    )


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


def create_sub(client, name="test", allow_polls=False):
    rv = client.get(url_for("subs.create_sub"))
    assert rv.status_code == 200

    data = {"csrf_token": csrf_token(rv.data), "subname": name, "title": "Testing"}

    rv = client.post(url_for("subs.create_sub"), data=data, follow_redirects=True)

    assert b"/s/" + name.encode("utf-8") in rv.data


def promote_user_to_admin(client, user_info):
    """Assuming user_info is the info for the logged-in user, promote them
    to admin and leave them logged in.
    """
    log_out_current_user(client)
    admin = User.get(fn.Lower(User.name) == user_info["username"])
    UserMetadata.create(uid=admin.uid, key="admin", value="1")
    log_in_user(client, user_info)
