import json
import pytest

from flask import url_for
from app import mail

from pytest_flask.fixtures import client
from test.fixtures import*
from test.utilities import csrf_token, pp, promote_user_to_admin
from test.utilities import register_user, log_in_user, log_out_current_user

def test_admin_can_ban_and_unban_user(client, user_info, user2_info):
    register_user(client, user_info)
    register_user(client, user2_info)
    promote_user_to_admin(client, user2_info)

    username = user_info['username']

    rv = client.get(url_for('user.view', user=username))
    rv = client.post(url_for('do.ban_user', username=username),
                     data=dict(csrf_token=csrf_token(rv.data)),
                     follow_redirects=True)

    # For now, banning makes you unable to log in.
    log_out_current_user(client)
    log_in_user(client, user_info, expect_success=False)
    log_in_user(client, user2_info, expect_success=True)

    rv = client.get(url_for('user.view', user=username))
    rv = client.post(url_for('do.unban_user', username=username),
                     data=dict(csrf_token=csrf_token(rv.data)),
                     follow_redirects=True)

    log_out_current_user(client)
    log_in_user(client, user_info, expect_success=True)


@pytest.mark.parametrize('test_config', [{'auth': {'require_valid_emails': True}}])
def test_admin_can_ban_email_domain(client, user_info):
    register_user(client, user_info)
    promote_user_to_admin(client, user_info)

    rv = client.get(url_for('admin.domains', domain_type='email'))
    rv = client.post(url_for('do.ban_domain', domain_type='email'),
                     data=dict(csrf_token=csrf_token(rv.data),
                               domain='spam4u.com'),
                     follow_redirects=True)
    reply = json.loads(rv.data.decode('utf-8'))
    assert reply['status'] == 'ok'

    log_out_current_user(client)
    rv = client.get(url_for('auth.register'))
    with mail.record_messages() as outbox:
        data = dict(csrf_token=csrf_token(rv.data),
                    username='troll',
                    password='Safe123#$@lolnot',
                    confirm='Safe123#$@lolnot',
                    email_required='troll@spam4u.com',
                    invitecode='',
                    accept_tos=True,
                    captcha='xyzzy')
        rv = client.post(url_for('auth.register'), data=data, follow_redirects=True)
        assert len(outbox) == 0
        assert b'do not accept emails' in rv.data
        assert b'Register' in rv.data
        assert b'Log out' not in rv.data
