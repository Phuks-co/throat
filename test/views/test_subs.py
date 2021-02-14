import datetime
import re
import pytest
from flask import url_for
from test.utilities import register_user, csrf_token, create_sub
from app.models import Sub, SubMetadata


def get_error(data):
    f = re.findall(rb'<div class=\"error\".*?>(.+?)</div>', data)
    return f[0] if f else b""


def test_create_sub_error(client, user_info):
    register_user(client, user_info)
    rv = client.get(url_for('subs.create_sub'))
    assert rv.status_code == 200

    data = {
        'csrf_token': csrf_token(rv.data),
        'subname': 'ñññ',
        'title': 'Testing'
    }
    rv = client.post(url_for('subs.create_sub'), data=data, follow_redirects=True)
    assert b'Sub name has invalid characters' in get_error(rv.data)
    data['subname'] = 'home'
    rv = client.post(url_for('subs.create_sub'), data=data, follow_redirects=True)
    assert b'Invalid sub name' in get_error(rv.data)
    data['subname'] = 'test'
    rv = client.post(url_for('subs.create_sub'), data=data, follow_redirects=True)
    assert b'You must be at least level 2.' in get_error(rv.data)


@pytest.mark.parametrize('test_config', [{'site': {'sub_creation_min_level': 0}}])
def test_create_sub(client, user_info, test_config):
    register_user(client, user_info)
    rv = client.get(url_for('subs.create_sub'))
    assert rv.status_code == 200

    data = {
        'csrf_token': csrf_token(rv.data),
        'subname': 'test',
        'title': 'Testing'
    }

    rv = client.post(url_for('subs.create_sub'), data=data, follow_redirects=True)
    assert not get_error(rv.data)
    assert b'/s/test' in rv.data

    # if we try again it should fail
    rv = client.post(url_for('subs.create_sub'), data=data, follow_redirects=True)
    assert b'Sub is already registered' == get_error(rv.data)


def test_submit_page(client, user_info):
    register_user(client, user_info)
    rv = client.get(url_for('subs.submit', ptype='text'))
    assert rv.status_code == 200
    rv = client.get(url_for('subs.submit', ptype='link'))
    assert rv.status_code == 200
    rv = client.get(url_for('subs.submit', ptype='poll'))
    assert rv.status_code == 200
    rv = client.get(url_for('subs.submit', ptype='upload'))
    assert rv.status_code == 200
    rv = client.get(url_for('subs.submit', ptype='something_that_does_not_exist'))
    assert rv.status_code == 404

    rv = client.get(url_for('subs.submit', ptype='text', sub='sub_that_does_not_exist'))
    assert rv.status_code == 404


@pytest.mark.parametrize('test_config', [{'site': {'sub_creation_min_level': 0}}])
def test_submit_text_post(client, user_info, test_config):
    register_user(client, user_info)
    create_sub(client)
    rv = client.get(url_for('subs.submit', ptype='text', sub='test'))
    data = {
        'csrf_token': csrf_token(rv.data),
        'title': 'f\u000A\u000A\u000A'
    }

    rv = client.post(url_for('subs.submit', ptype='text', sub='does_not_exist'), data=data, follow_redirects=True)
    assert b'Sub does not exist' in get_error(rv.data)
    rv = client.post(url_for('subs.submit', ptype='text', sub='test'), data=data, follow_redirects=True)
    assert b"Error in the 'Post type' field - This field is required." == get_error(rv.data)
    data['ptype'] = 'text'
    rv = client.post(url_for('subs.submit', ptype='text', sub='test'), data=data, follow_redirects=True)
    assert b'Title is too short and/or contains whitespace characters.' in get_error(rv.data)
    data['title'] = 'Testing!'
    rv = client.post(url_for('subs.submit', ptype='text', sub='test'), data=data, follow_redirects=True)
    assert not get_error(rv.data)
    assert b'Testing! |  test' in rv.data


@pytest.mark.parametrize('test_config', [{'site': {'sub_creation_min_level': 0}}])
def test_submit_link_post(client, user_info, test_config):
    register_user(client, user_info)
    create_sub(client)
    rv = client.get(url_for('subs.submit', ptype='text', sub='test'))
    data = {
        'csrf_token': csrf_token(rv.data),
        'title': 'Testing link!',
        'ptype': 'link'
    }

    rv = client.post(url_for('subs.submit', ptype='link', sub='test'), data=data, follow_redirects=False)
    assert get_error(rv.data) == b'No link provided.'
    data['link'] = 'https://google.com'
    rv = client.post(url_for('subs.submit', ptype='link', sub='test'), data=data, follow_redirects=False)
    assert rv.status_code == 302
    assert '/s/test/1' == rv.location

    # Test anti-repost
    rv = client.post(url_for('subs.submit', ptype='link', sub='test'), data=data, follow_redirects=False)
    assert get_error(rv.data) == b'This link was <a href="/s/test/1">recently posted</a> on this sub.'


@pytest.mark.parametrize('test_config', [{'site': {'sub_creation_min_level': 0}}])
def test_submit_poll_post(client, user_info, test_config):
    register_user(client, user_info)
    create_sub(client)

    rv = client.get(url_for('subs.submit', ptype='text', sub='test'))
    data = {
        'csrf_token': csrf_token(rv.data),
        'title': 'Testing poll!',
        'ptype': 'poll',
        'hideresults': '1'
    }
    rv = client.post(url_for('subs.submit', ptype='text', sub='test'), data=data, follow_redirects=False)
    assert get_error(rv.data) == b'That post type is not allowed in this sub.'
    sub = Sub.get(Sub.name == 'test')
    SubMetadata.create(sid=sub.sid, key='allow_polls', value=1)
    rv = client.post(url_for('subs.submit', ptype='text', sub='test'), data=data, follow_redirects=False)
    assert get_error(rv.data) == b'Not enough poll options provided.'
    data['options-0'] = 'Test 1'
    data['options-1'] = 'Test 2'
    data['options-2'] = 'Test 3' * 60
    data['closetime'] = 'asdf'
    rv = client.post(url_for('subs.submit', ptype='text', sub='test'), data=data, follow_redirects=False)
    assert get_error(rv.data) == b'Poll option text is too long.'
    data['options-2'] = 'Test 3'
    rv = client.post(url_for('subs.submit', ptype='text', sub='test'), data=data, follow_redirects=False)
    assert get_error(rv.data) == b'Invalid closing time.'
    data['closetime'] = (datetime.datetime.utcnow() - datetime.timedelta(days=2)).isoformat() + 'Z'
    rv = client.post(url_for('subs.submit', ptype='text', sub='test'), data=data, follow_redirects=False)
    assert get_error(rv.data) == b'The closing time is in the past!'
    data['closetime'] = (datetime.datetime.utcnow() + datetime.timedelta(days=62)).isoformat() + 'Z'
    rv = client.post(url_for('subs.submit', ptype='text', sub='test'), data=data, follow_redirects=False)
    assert get_error(rv.data) == b'Poll closing time is too far in the future.'
    data['closetime'] = (datetime.datetime.utcnow() + datetime.timedelta(days=2)).isoformat() + 'Z'
    rv = client.post(url_for('subs.submit', ptype='text', sub='test'), data=data, follow_redirects=False)
    assert get_error(rv.data) == b''
    assert '/s/test/1' == rv.location


@pytest.mark.parametrize('test_config', [{'site': {'sub_creation_min_level': 0}}])
def test_submit_invalid_post_type(client, user_info, test_config):
    register_user(client, user_info)
    create_sub(client)
    rv = client.get(url_for('subs.submit', ptype='text', sub='test'))
    data = {
        'csrf_token': csrf_token(rv.data),
        'title': 'Testing link!',
    }

    rv = client.post(url_for('subs.submit', ptype='toast', sub='test'), data=data, follow_redirects=False)
    assert rv.status_code == 404


@pytest.mark.parametrize('test_config', [{'site': {'sub_creation_min_level': 0}}])
def test_random_sub(client, user_info, test_config):
    register_user(client, user_info)
    create_sub(client)
    rv = client.get(url_for('subs.random_sub'), follow_redirects=False)
    assert rv.status_code == 302
    assert '/s/test' == rv.location
