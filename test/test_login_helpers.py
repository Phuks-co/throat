from flask.helpers import url_for


def test_admins_get_200_on_admin_index(client, an_admin) -> None:
    # Attempt to get the admin page.
    response = client.get(url_for("admin.index"))
    # Admins receive a 200 OK response.
    assert response == 200


def test_non_admins_get_404_on_admin_index(client, a_user) -> None:
    # Attempt to get the admin page.
    response = client.get(url_for("admin.index"))
    # Non-admin users receive a 404 Not Found response.
    # (Perhaps it should be 403 really?)
    assert response == 404


def test_anonymous_users_get_302_on_admin_index(client) -> None:
    # Attempt to get the admin page.
    response = client.get(url_for("admin.index"))
    # Anonymous users receive a 302 Found response
    # and are redirected to the login page.
    assert response == 302
    assert response.location.startswith(url_for("auth.login"))
