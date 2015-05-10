import os

os.environ['PYDRILL_CONFIG'] = os.path.join(os.path.dirname(__file__), 'pydrill.cfg')

import pytest
from flask import session

from pydrill.app import app, db, redis_store
# TODO: how can we import models/views automatically?
from pydrill import views  # noqa
from pydrill import models
from pydrill.utils import User


MAC_USER_AGENT = ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 '
                  '(KHTML, like Gecko) Chrome/41.0.2227.1 Safari/537.36')

LINUX_USER_AGENT = ('Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 '
                    '(KHTML, like Gecko) Chrome/41.0.2227.0 Safari/537.36')


@pytest.fixture(autouse=True)
def flush_redis_db():
    redis_store.flushdb()


@pytest.fixture(autouse=True)
def flush_sql_db():
    db.drop_all()
    db.create_all()
    tests_dir = os.path.dirname(__file__)
    questions_dir = os.path.join(os.path.dirname(tests_dir), 'questions')
    models.load_questions(questions_dir)


def test_new_user():
    with app.test_client() as c:
        check_get(c, '/q/average/', STEVE)
        user = User(**session['user'])
        user_id = user.id
        assert len(user.id) == 36  # length of str(uuid4) is 36
        assert user.score == 0
        assert user.teams == ['Apple']
        assert redis_store.hgetall('team:Apple') == {'num_users': '1', 'score_sum': '0'}

        # id is given once
        check_get(c, '/q/average/', STEVE)
        assert User(**session['user']).id == user_id


def test_questions():
    assert models.Question.query.count() == 2


def test_correct_answer():
    with app.test_client() as c:
        # TODO: DRY it up with test_new_user
        check_get(c, '/q/average/', STEVE)
        question = models.Question.query.get('average')
        correct = question.answers.filter_by(is_correct=True).first()
        check_post(c, '/a/average/{:d}/'.format(correct.id), STEVE)
        # TODO: use g.user maybe?
        user = User(**session['user'])
        assert user.score == 1
        # TODO: check team scores


# TODO: test that answering the same question twice correctly increases score only once
# TODO: check that redirect is to the new question
# TODO: check that when there's no new question redirect is to the random question


STEVE = dict(environ_base={'HTTP_USER_AGENT': MAC_USER_AGENT,
                           'HTTP_REFERER': 'parse this'})
PAUL = dict(environ_base={'HTTP_USER_AGENT': LINUX_USER_AGENT,
                          'HTTP_REFERER': 'https://news.ycombinator.com/item?id=test'})


def check_get(client, url, user):
    rv = client.get(url, **user)
    print(rv.data)
    assert rv.status_code == 200
    return rv


def check_post(client, url, user):
    rv = client.post(url, **user)
    assert rv.status_code == 302
    return rv
