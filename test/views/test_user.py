from flask import url_for
from test.utilities import register_user


def test_settings_page(client, user_info):
    register_user(client, user_info)
    username = user_info["username"]
    assert client.get(url_for("user.edit_user", user=username)).status_code == 200
