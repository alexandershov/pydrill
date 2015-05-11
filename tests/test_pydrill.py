import os

os.environ['PYDRILL_CONFIG'] = os.path.join(os.path.dirname(__file__), 'pydrill.cfg')

import pytest
from flask import session

from pydrill import app, db, redis_store
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
    questions_dir = os.path.join(os.path.dirname(__file__), 'questions')
    models.load_questions(questions_dir)


def get_user():
    return User(**session['user'])


def test_new_user():
    with app.test_client() as c:
        check_get(c, '/ask/average/', PAUL)
        user = get_user()
        user_id = user.id
        assert len(user.id) == 36  # length of str(uuid4) is 36
        assert user.score == 0
        assert_same_items(user.teams, ['Linux', 'Hacker News'])
        assert redis_store.hgetall('team:Linux') == {'num_users': '1', 'score_sum': '0'}
        assert redis_store.hgetall('team:Hacker News') == {'num_users': '1', 'score_sum': '0'}

        # id doesn't change after the first visit
        check_get(c, '/ask/average/', PAUL)
        assert get_user().id == user_id


def test_questions():
    assert models.Question.query.count() == 2


@pytest.mark.parametrize('question_id, are_correct, scores', [
    # only the first correct answer can increase the score
    ('average', [True, True], [1, 1]),
    ('average', [False, True], [0, 0]),
])
# TODO: more specific name
def test_correct_answer(question_id, are_correct, scores):
    assert len(are_correct) == len(scores)
    with app.test_client() as c:
        for is_correct, score in zip(are_correct, scores):
            answer_question(c, question_id, is_correct=is_correct, user=STEVE)
            # TODO: do something better for checking team scores
            assert redis_store.hgetall('team:Apple') == {'num_users': '1', 'score_sum': str(score)}


@pytest.mark.parametrize('question_ids, redirect_path', [
    (['average'], '/ask/static-decorator/'),
    (['static-decorator'], '/ask/average/'),
    (['average', 'static-decorator'], None),  # no unanswered question, any path will do
])
def test_redirects(question_ids, redirect_path):
    with app.test_client() as c:
        for i, question_id in enumerate(question_ids):
            rv = answer_question(c, question_id, is_correct=True, user=STEVE)
            if i == len(question_ids) - 1:
                if redirect_path is not None:
                    assert rv.location.endswith(redirect_path)


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


def get_answer(question, is_correct):
    return question.answers.filter_by(is_correct=is_correct).first()


def get_correct_answer(question):
    return get_answer(question, is_correct=True)


def get_any_wrong_answer(question):
    return get_answer(question, is_correct=False)


# TODO: avoid passing client to all functions
def answer_question(client, question_id, is_correct, user):
    question = models.Question.query.get(question_id)
    url = '/answer/{}/{:d}/'.format(question_id, get_answer(question, is_correct).id)
    rv = check_post(client, url, user)
    return rv
