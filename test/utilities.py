from bs4 import BeautifulSoup
from flask import url_for
from app import mail
from app.auth import email_validation_is_required


def csrf_token(data):
    soup = BeautifulSoup(data, 'html.parser')
    # print(soup.prettify())
    return soup.find(id='csrf_token')['value']


def get_value(data, key):
    soup = BeautifulSoup(data, 'html.parser')
    # print(soup.prettify())
    return soup.find(id=key)['value']


# pretty-print for debugging purposes
def pp(data):
    print(BeautifulSoup(data, 'html.parser').prettify())


def recursively_update(dictionary, new_values):
    for elem in new_values.keys():
        if (elem in dictionary.keys() and
                isinstance(new_values[elem], dict) and
                isinstance(dictionary[elem], dict)):
            recursively_update(dictionary[elem], new_values[elem])
        else:
            dictionary[elem] = new_values[elem]


def log_in_user(client, user_info, expect_success=True):
    """Log in the user described by the user_info directory.  User should
already be registered."""
    rv = client.get(url_for('auth.login'))
    rv = client.post(url_for('auth.login'),
                     data=dict(csrf_token=csrf_token(rv.data),
                               username=user_info['username'],
                               password=user_info['password']),
                     follow_redirects=True)
    if expect_success:
        assert b'Log out' in rv.data
    else:
        assert b'Log in' in rv.data


def log_out_current_user(client, verify=True):
    """Log out the user who is logged in."""
    rv = client.get(url_for('home.index'))
    rv = client.post(url_for('do.logout'), data=dict(csrf_token=csrf_token(rv.data)),
                     follow_redirects=True)
    if verify:
        assert b'Log in' in rv.data


def register_user(client, user_info):
    """Register a user with the client and leave them logged in."""
    rv = client.get(url_for('home.index'))
    rv = client.post(url_for('do.logout'), data=dict(csrf_token=csrf_token(rv.data)),
                     follow_redirects=True)
    rv = client.get(url_for('auth.register'))
    with mail.record_messages() as outbox:
        data = dict(csrf_token=csrf_token(rv.data),
                    username=user_info['username'],
                    password=user_info['password'],
                    confirm=user_info['password'],
                    invitecode='',
                    accept_tos=True,
                    captcha='xyzzy')
        if email_validation_is_required():
            data['email_required'] = user_info['email']
        else:
            data['email_optional'] = user_info['email']

        rv = client.post(url_for('auth.register'),
                         data=data,
                         follow_redirects=True)

        if email_validation_is_required():
            message = outbox[-1]
            soup = BeautifulSoup(message.html, 'html.parser')
            token = soup.a['href'].split('/')[-1]
            rv = client.get(url_for('auth.login_with_token', token=token),
                            follow_redirects=True)
