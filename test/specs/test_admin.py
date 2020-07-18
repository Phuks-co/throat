import json
import pytest

from peewee import fn
from flask import url_for

from pytest_flask.fixtures import client
from test.fixtures import*
from test.utilities import csrf_token, pp
from test.utilities import register_user, log_in_user, log_out_current_user

def promote_user_to_admin(client, user_info):
    """Assuming user_info is the info for the logged-in user, promote them
    to admin and leave them logged in.
    """
    log_out_current_user(client)
    admin = User.get(fn.Lower(User.name) == user_info['username'])
    UserMetadata.create(uid=admin.uid, key='admin', value='1')
    log_in_user(client, user_info)


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
