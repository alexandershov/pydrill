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
        rv = c.get('/q/average/', environ_base={'HTTP_USER_AGENT': MAC_USER_AGENT})
        assert rv.status_code == 200
        user = User(**session['user'])
        # TODO: test that user.id stays the same during the subsequent visits
        assert len(user.id) == 36  # length of str(uuid4) is 36
        assert user.score == 0
        assert user.teams == ['Apple']
        assert redis_store.hgetall('team:Apple') == {'num_users': '1', 'score_sum': '0'}


def test_questions():
    assert models.Question.query.count() == 1


def test_correct_answer():
    with app.test_client() as c:
        # TODO: DRY it up with test_new_user
        rv = c.get('/q/average/', environ_base={'HTTP_USER_AGENT': MAC_USER_AGENT})
        assert rv.status_code == 200
        question = models.Question.query.get('average')
        correct = question.answers.filter_by(is_correct=True).first()
        rv = c.post('/a/average/{:d}/'.format(correct.id))
        assert rv.status_code == 302
        # TODO: use g.user maybe?
        user = User(**session['user'])
        assert user.score == 1
        # TODO: check team scores
