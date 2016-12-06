""" Basic unit tests """
import sys
import json
import unittest
import tempfile
import redis

sys.path.append('..')
from app import app, db  # noqa

# Misc setup common for all tests
r = redis.StrictRedis(host=app.config['CACHE_REDIS_HOST'],
                      port=app.config['CACHE_REDIS_PORT'])
r.flushall()
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + tempfile.mkstemp()[1]
app.config['WTF_CSRF_ENABLED'] = False
try:
    db.init_app(app)
except AssertionError:
    pass

with app.app_context():
    db.create_all()

app.config['TESTING'] = True

# -- Real shit starts here


class AABasicTestCase(unittest.TestCase):
    """ Here we test for pages loading, etc """
    def setUp(self):
        self.app = app.test_client()

    def test_index_loads_and_database_is_empty(self):
        """ Tests if the index loads """
        x = self.app.get('/')
        assert 'There are no posts here, yet.' in x.get_data(True)
        assert x.status_code == 200


class ABAccountTestCase(unittest.TestCase):
    """ Here we test registration, login and logout """
    def setUp(self):
        self.app = app.test_client()

    def register(self, user, password):
        """ Registers an account """
        return self.app.post('/do/register', data={'username': user,
                                                   'password': password,
                                                   'confirm': password,
                                                   'accept_tos': '1'})

    def login(self, user, password):
        return self.app.post('/do/login', data={'username': user,
                                                'password': password})

    def create_sub(self, name, title):
        return self.app.post('/do/create_sub', data={'subname': name,
                                                     'title': title})

    def text_post(self, sub, title, content):
        return self.app.post('/do/txtpost', data={'sub': sub,
                                                  'title': title,
                                                  'content': content})

    def link_post(self, sub, title, link):
        return self.app.post('/do/lnkpost', data={'sub': sub,
                                                  'title': title,
                                                  'link': link})

    def test_accounts(self):
        """ Tests if registration works (not the captcha) """
        x = self.register('foo', 'foofoofoobar')
        x = json.loads(x.get_data(True))
        assert x['status'] == 'ok'
        x = self.login('foo', 'foofoofoobar')
        x = json.loads(x.get_data(True))
        assert x['status'] == 'ok'
        x = self.app.post('/do/logout')
        assert x.status_code == 302

    def test_sub(self):
        self.login('foo', 'foofoofoobar')
        x = self.create_sub('testing', 'not regular testing. UNIT testing.')
        x = json.loads(x.get_data(True))
        assert x['status'] == 'ok'
        # empty sub page tests
        x = self.app.get('/s/testing/hot')
        assert 'There are no posts here, yet.' in x.get_data(True)
        x = self.app.get('/s/testing/top')
        assert 'There are no posts here, yet.' in x.get_data(True)
        x = self.app.get('/s/testing/new')
        assert 'There are no posts here, yet.' in x.get_data(True)
        # posting tests
        x = self.text_post('testing', 'yo im testing', '# yeah, test')
        p = json.loads(x.get_data(True))
        assert p['status'] == 'ok'
        x = self.app.get('/s/testing/{0}'.format(p['pid']))
        assert 'yo im testing' in x.get_data(True)

        x = self.link_post('testing', 'still testing', 'https://google.com')
        p = json.loads(x.get_data(True))
        assert p['status'] == 'ok'
        x = self.app.get('/s/testing/{0}'.format(p['pid']))
        assert 'still testing' in x.get_data(True)

        # NOT empty subpage tests :)
        x = self.app.get('/s/testing/hot')
        assert 'There are no posts here, yet.' not in x.get_data(True)
        x = self.app.get('/s/testing/top')
        assert 'There are no posts here, yet.' not in x.get_data(True)
        x = self.app.get('/s/testing/new')
        assert 'There are no posts here, yet.' not in x.get_data(True)

        r.flushall()
        x = self.app.get('/')
        assert 'There are no posts here, yet.' not in x.get_data(True)


if __name__ == '__main__':
    unittest.main()
