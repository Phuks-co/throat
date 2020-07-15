import json
import pytest

from peewee import fn

from test.fixtures import *
from test.utilities import csrf_token, pp

def promote_user_to_admin(client, user_info):
    """Assuming user_info is the info for the logged-in user, promote them
    to admin and leave them logged in.
    """
    rv = client.get('/')
    rv = client.post('/do/logout', data=dict(csrf_token=csrf_token(rv.data)),
                     follow_redirects=True)
    assert b'Log in' in rv.data

    admin = User.get(fn.Lower(User.name) == user_info['username'])
    UserMetadata.create(uid=admin.uid, key='admin', value='1')

    rv = client.get('/login')
    rv = client.post('/login', data=dict(csrf_token=csrf_token(rv.data),
                                         username=user_info['username'],
                                         password=user_info['password']),
                     follow_redirects=True)
    assert b'Log out' in rv.data


def test_admin_can_ban_and_unban_user(client, user_info, user2_info):
    register_user(client, user_info)
    register_user(client, user2_info)
    promote_user_to_admin(client, user2_info)

    username = user_info['username']
    print("username=", username)

    rv = client.get(f'/u/{username}')
    rv = client.post(f'/do/admin/ban_user/{username}',
                     data=dict(csrf_token=csrf_token(rv.data)),
                     follow_redirects=True)

    # TO DO, test based on functionality
    user = User.get(fn.Lower(User.name) == username)
    assert user.status == 5

    help(client.post)
    rv = client.get(f'/u/{username}')
    rv = client.post(f'/do/admin/unban_user/{username}',
                     data=dict(csrf_token=csrf_token(rv.data)),
                     follow_redirects=True)
    print(rv.status)
    pp(rv.data)

    # TO DO, test based on functionality
    user = User.get(fn.Lower(User.name) == username)
    assert user.status == 0
