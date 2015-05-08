import pytest

from flask import session

from pydrill.app import app, redis_store
# TODO: how can we import views automatically?
from pydrill import views  # noqa


MAC_USER_AGENT = ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 '
                  '(KHTML, like Gecko) Chrome/41.0.2227.1 Safari/537.36')


# TODO: use redis db #1 for tests (#0 is used for development/production)
@pytest.fixture(autouse=True)
def flush_redis_db():
    redis_store.flushdb()


def test_new_user():
    with app.test_client() as c:
        c.get('/q/', environ_base={'HTTP_USER_AGENT': MAC_USER_AGENT})
        assert len(session['user'].id) == 36  # length of str(uuid4) is 36
        assert session['user'].score == 0
        assert session['user'].teams == ['Apple']
        assert redis_store.hgetall('team:Apple') == {'num_users': '1', 'score_sum': '0'}
