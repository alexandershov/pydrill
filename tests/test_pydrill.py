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


def get_user():
    return User(**session['user'])


def test_new_user():
    with app.test_client() as c:
        check_get(c, '/q/average/', PAUL)
        user = get_user()
        user_id = user.id
        assert len(user.id) == 36  # length of str(uuid4) is 36
        assert user.score == 0
        assert_same_items(user.teams, ['Linux', 'Hacker News'])
        assert redis_store.hgetall('team:Linux') == {'num_users': '1', 'score_sum': '0'}
        assert redis_store.hgetall('team:Hacker News') == {'num_users': '1', 'score_sum': '0'}

        # id doesn't change after the first visit
        check_get(c, '/q/average/', PAUL)
        assert get_user().id == user_id


def test_questions():
    assert models.Question.query.count() == 2


def test_correct_answer():
    with app.test_client() as c:
        check_get(c, '/q/average/', STEVE)
        question = models.Question.query.get('average')
        correct = get_correct_answer(question)
        url = '/a/average/{:d}/'.format(correct.id)
        check_post(c, url, STEVE)
        assert get_user().score == 1

        # only the first answer can increase the score
        # TODO: test that first wrong, second correct doesn't increase score as well
        check_post(c, url, STEVE)
        assert get_user().score == 1
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
    assert rv.status_code == 200
    return rv


def check_post(client, url, user):
    rv = client.post(url, **user)
    assert rv.status_code == 302
    return rv


def assert_same_items(xs, ys):
    assert sorted(xs) == sorted(ys)


def get_correct_answer(question):
    return question.answers.filter_by(is_correct=True).first()
