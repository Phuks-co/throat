import json
import pytest
from bs4 import BeautifulSoup
from flask import url_for

from app import mail
from app.config import config
from app.auth import auth_provider, email_validation_is_required

from pytest_flask.fixtures import client
from test.fixtures import *
from test.utilities import csrf_token, pp
from test.utilities import register_user, log_in_user, log_out_current_user


@pytest.mark.parametrize('test_config', [{'auth': {'validate_emails': True}},
                                         {'auth': {'validate_emails': False}}])
def test_registration_login(client):
    """The registration page logs a user in if they register correctly."""
    rv = client.get(url_for('auth.register'))
    with mail.record_messages() as outbox:
        data = dict(csrf_token=csrf_token(rv.data),
                    username='supertester',
                    password='Safe123#$@lolnot',
                    confirm='Safe123#$@lolnot',
                    invitecode='',
                    accept_tos=True,
                    captcha='xyzzy')
        if email_validation_is_required():
            data['email_required'] = 'test@example.com'
        else:
            data['email_optional'] = 'test@example.com'
        rv = client.post(url_for('auth.register'), data=data, follow_redirects=True)

        if email_validation_is_required():
            assert b'spam' in rv.data  # Telling user to go check it.
            message = outbox[-1]
            soup = BeautifulSoup(message.html, 'html.parser')
            token = soup.a['href'].split('/')[-1]
            rv = client.get(url_for('auth.login_with_token', token=token),
                            follow_redirects=True)

        assert auth_provider.get_user_by_email('test@example.com').name == 'supertester'
        assert b'Log out' in rv.data


@pytest.mark.parametrize('test_config', [{'auth': {'validate_emails': True}}])
def test_email_required_for_registration(client, user_info):
    "If emails are required, trying to register without one will fail."
    rv = client.get(url_for('auth.register'))
    with mail.record_messages() as outbox:
        data = dict(csrf_token=csrf_token(rv.data),
                    username='supertester',
                    password='Safe123#$@lolnot',
                    confirm='Safe123#$@lolnot',
                    email_required='',
                    invitecode='',
                    accept_tos=True,
                    captcha='xyzzy')
        rv = client.post(url_for('auth.register'), data=data, follow_redirects=True)
        assert len(outbox) == 0
        assert b'Error' in rv.data
        assert b'Register' in rv.data
        assert b'Log out' not in rv.data


# @pytest.mark.parametrize('test_config', [{'auth': {'validate_emails': True}}])
# def test_login_before_confirming_email():
#     """Registered users with unconfirmed emails can't log in."""
#     # It should give them the option of sending another link.
#     pass


# TODO make sure this can be done with unicode in password
def test_logout_and_login_again(client, user_info):
    """A logged in user can log out and back in again."""
    register_user(client, user_info)
    assert b'Log out' in client.get(url_for('home.index')).data
    log_out_current_user(client, verify=True)
    log_in_user(client, user_info, expect_success=True)


# def test_reset_password_by_email():
#     """A user can reset their password using a link received by email."""
#     pass


def test_change_password(client, user_info):
    """A user can change their password and log in with the new password."""
    register_user(client, user_info)
    new_password = 'mynewSuperSecret#123'
    assert new_password != user_info['password']
    rv = client.get(url_for('user.edit_password'))
    rv = client.post(url_for('do.edit_user_password'),
                     data=dict(csrf_token=csrf_token(rv.data),
                               oldpassword=user_info['password'],
                               password=new_password,
                               confirm=new_password),
                     follow_redirects=True)
    reply = json.loads(rv.data.decode('utf-8'))
    assert reply['status'] == 'ok'

    log_out_current_user(client)

    # Try to log in with the old password
    log_in_user(client, user_info, expect_success=False)

    new_info = dict(user_info)
    new_info.update(password=new_password)
    log_in_user(client, new_info, expect_success=True)


# def test_change_user_email():
#     """A user can change their email address, and receive a reset password
#     link at the new address."""
#     pass


def test_delete_account(client, user_info):
    """A user can delete their account."""
    register_user(client, user_info)

    # The password has to be right.
    rv = client.get(url_for('user.delete_account'))
    rv = client.post(url_for('do.delete_user'),
                     data=dict(csrf_token=csrf_token(rv.data),
                               password='ThisIsNotTheRightPassword',
                               consent='YES'),
                     follow_redirects=True)
    reply = json.loads(rv.data.decode('utf-8'))
    assert reply['status'] == 'error'

    # The consent must be given.
    rv = client.get(url_for('user.delete_account'))
    rv = client.post(url_for('do.delete_user'),
                     data=dict(csrf_token=csrf_token(rv.data),
                               password='ThisIsNotTheRightPassword',
                               consent='NO'),
                     follow_redirects=True)
    reply = json.loads(rv.data.decode('utf-8'))
    assert reply['status'] == 'error'

    rv = client.get(url_for('user.delete_account'))
    rv = client.post(url_for('do.delete_user'),
                     data=dict(csrf_token=csrf_token(rv.data),
                               password=user_info['password'],
                               consent='YES'),
                     follow_redirects=True)
    reply = json.loads(rv.data.decode('utf-8'))
    assert reply['status'] == 'ok'

    # Deleting your account should log you out.
    rv = client.get(url_for('home.index'))
    assert b'Log in' in rv.data

    # Try to log in to the deleted account.
    log_in_user(client, user_info, expect_success=False)



# TODO deleted users should be able to make a new account with the
# same email but banned users should not
