import pytest
from bs4 import BeautifulSoup
from flask import current_app

from app import mail

from test.fixtures import test_config, client


# This is intended as a sample first test, not a real test of login
# functionality. All it does is check that somewhere in the login page
# is the string "password".
def test_login(client):
    """The login page mentions passwords."""
    rv = client.get('/login')
    assert b'password' in rv.data


@pytest.mark.parametrize('test_config', [{'auth': {'validate_emails': True}},
                                         {'auth': {'validate_emails': False}}])
def test_registration_login(client):
    """The registration page logs a user in if they register correctly."""
    rv = client.get('/register')
    with mail.record_messages() as outbox:
        rv = client.post('/register',
                         data=dict(csrf_token=csrf_token(rv.data),
                                   username='supertester',
                                   email='test@example.com',
                                   password='Safe123#$@lolnot',
                                   confirm='Safe123#$@lolnot',
                                   invitecode='',
                                   accept_tos=True,
                                   captcha='xyzzy'),
                         follow_redirects=True)

        if current_app.config['THROAT_CONFIG'].auth.validate_emails:
            message = outbox[-1]
            soup = BeautifulSoup(message.html, 'html.parser')
            token = soup.a['href'].split('/')[-1]
            rv = client.get("login/with-token/" + token,
                            follow_redirects=True)
        assert b'Log out' in rv.data


def csrf_token(data):
    soup = BeautifulSoup(data, "html.parser")
    # print(soup.prettify())
    return soup.find(id="csrf_token")["value"]
