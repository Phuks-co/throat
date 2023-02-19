import pytest
import pyotp
from flask import url_for

from app.models import UserMetadata, User
from test.utilities import register_user, promote_user_to_admin, csrf_token


@pytest.mark.parametrize("test_config", [{"site": {"enable_totp": True}}])
def test_totp_required(client, user_info, test_config):
    register_user(client, user_info)
    promote_user_to_admin(client, user_info)
    rv = client.get(url_for("admin.index"))
    assert rv.status_code == 302
    assert rv.location == url_for("admin.auth")


@pytest.mark.parametrize("test_config", [{"site": {"enable_totp": True}}])
def test_admin_totp_auth_flow(client, user_info, test_config):
    register_user(client, user_info)
    assert client.get(url_for("admin.auth")).status_code == 404
    promote_user_to_admin(client, user_info)
    rv = client.get(url_for("admin.auth"), follow_redirects=True)
    assert rv.status_code == 200
    assert b"TOTP setup" in rv.data
    user = User.get(User.name == user_info["username"])
    user_secret = UserMetadata.get(
        (UserMetadata.uid == user.uid) & (UserMetadata.key == "totp_secret")
    )
    totp = pyotp.TOTP(user_secret.value)

    data = {"csrf_token": csrf_token(rv.data), "totp": totp.now()}

    rv = client.post(url_for("admin.auth"), data=data, follow_redirects=False)
    assert rv.status_code == 302
    assert rv.location == url_for("admin.index")

    # Try again with bad token
    data["totp"] = "1"
    rv = client.post(url_for("admin.auth"), data=data, follow_redirects=False)
    assert rv.status_code == 200
    assert b"Invalid or expired token." in rv.data

    # # Check if we're actually logged in.
    # assert client.get(url_for("admin.index")).status_code == 200

    # Get QR code after we already set up TOTP
    assert client.get(url_for("admin.get_totp_image")).status_code == 403

    # Try logging out.
    client.post(url_for("admin.logout"), data=data)
    assert client.get(url_for("admin.index"), follow_redirects=False).status_code == 302


@pytest.mark.parametrize("test_config", [{"site": {"enable_totp": True}}])
def test_get_totp_image(client, user_info, test_config):
    register_user(client, user_info)
    assert client.get(url_for("admin.get_totp_image")).status_code == 404
    promote_user_to_admin(client, user_info)
    rv = client.get(url_for("admin.get_totp_image"))
    assert rv.status_code == 200
    assert rv.content_type == "image/png"
