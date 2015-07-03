import os
import random
import re
from flask.testing import FlaskClient

EASY_Q = 'average'
MEDIUM_Q = 'static-decorator'
HARD_Q = 'assign-to-empty-list'

os.environ['PYDRILL_CONFIG'] = os.path.join(os.path.dirname(__file__), 'pydrill.cfg')

import pytest
from flask import session

from pydrill import app, db, redis_store
from pydrill import models
from pydrill.jinja_env import get_score_text
from pydrill.utils import User

MAC_USER_AGENT = ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 '
                  '(KHTML, like Gecko) Chrome/41.0.2227.1 Safari/537.36')

LINUX_USER_AGENT = ('Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 '
                    '(KHTML, like Gecko) Chrome/41.0.2227.0 Safari/537.36')

MAC_USER_WITH_BAD_REFERER = {'HTTP_USER_AGENT': MAC_USER_AGENT,
                             'HTTP_REFERER': 'parse this'}

LINUX_USER_WITH_HN_REFERER = {'HTTP_USER_AGENT': LINUX_USER_AGENT,
                              'HTTP_REFERER': 'https://news.ycombinator.com/item?id=test'}

MAC_USER = {'HTTP_USER_AGENT': MAC_USER_AGENT}


# TODO: switch to app.test_client when Flask 1.0 is ready
def new_test_client(environ_base, *args, **kwargs):
    """Copy-pasted from Flask.test_client because we need to pass environ_base in .get() and .post()
    which test_client can do only from version 1.0 which is not production ready yet.
    """
    return Client(environ_base, app, app.response_class, *args, **kwargs)


class Client(FlaskClient):
    def __init__(self, environ_base, *args, **kwargs):
        self.__environ_base = environ_base
        super(Client, self).__init__(*args, **kwargs)

    def get(self, *args, **kwargs):
        return super(Client, self).get(*args, environ_base=self.__environ_base, **kwargs)

    def post(self, *args, **kwargs):
        return super(Client, self).post(*args, environ_base=self.__environ_base, **kwargs)


@pytest.fixture(autouse=True)
def flush_redis_db():
    redis_store.flushdb()


@pytest.fixture(autouse=True, scope='session')
def create_sql_db():
    db.drop_all()
    db.create_all()
    questions_dir = os.path.join(os.path.dirname(__file__), 'questions')
    models.load_questions(questions_dir)


@pytest.fixture(autouse=True)
def run_app_in_testing_mode():
    app.config['TESTING'] = True


@pytest.fixture()
def steve():
    return new_test_client(MAC_USER_WITH_BAD_REFERER)


@pytest.fixture()
def paul():
    return new_test_client(LINUX_USER_WITH_HN_REFERER)


@pytest.fixture()
def tim():
    return new_test_client(MAC_USER)


def get_user():
    return User(**session['user'])


def test_new_user(paul):
    with paul:
        ask_question(paul, EASY_Q)
        user = get_user()
        assert len(user.id) == 36  # length of str(uuid4) is 36
        assert user.score == 0
        assert_same_items(user.teams, ['Linux', 'Hacker News'])

        assert_team_score('Linux', num_users=1, score_sum=0)
        assert_team_score('Hacker News', num_users=1, score_sum=0)

        ask_question(paul, EASY_Q)
        # id doesn't change after the first visit
        assert get_user().id == user.id


def test_questions():
    assert models.Question.query.count() == 3


@pytest.mark.parametrize('question_id, are_correct, scores', [
    (EASY_Q, [True, True], [1, 1]),
    (EASY_Q, [False, True], [0, 0]),
])
def test_only_first_answer_can_increase_score(steve, question_id, are_correct, scores):
    assert len(are_correct) == len(scores)
    for is_correct, score in zip(are_correct, scores):
        answer_question(steve, question_id, is_correct=is_correct)
        assert_team_score('Apple', score_sum=score)


def matches_any_ask_url(*question_ids):
    parts = [r'/ask/{}/(\d+)/$'.format(q) for q in question_ids]
    return '|'.join(parts)


# TODO: test it separate tests with good naming maybe?
@pytest.mark.parametrize('question_ids, redirect_path_re', [
    ([EASY_Q], matches_any_ask_url(MEDIUM_Q, HARD_Q)),
    ([EASY_Q, MEDIUM_Q], matches_any_ask_url(HARD_Q)),
    ([EASY_Q, MEDIUM_Q, HARD_Q], matches_any_ask_url('.*'))
])
def test_answer_redirects(steve, question_ids, redirect_path_re):
    for i, question_id in enumerate(question_ids):
        rv = answer_question(steve, question_id, is_correct=random.choice([True, False]))
        if i == len(question_ids) - 1:
            # TODO: check that absolute url is correct
            assert re.search(redirect_path_re, rv.location)


def check_get(client, url):
    rv = client.get(url)
    assert rv.status_code == 200
    return rv


def check_post(client, url):
    rv = client.post(url)
    assert rv.status_code == 302
    return rv


def assert_same_items(xs, ys):
    assert sorted(xs) == sorted(ys)


def get_answer(question, is_correct):
    return question.answers.filter_by(is_correct=is_correct).first()


def get_correct_answer(question):
    return get_answer(question, is_correct=True)


def ask_question(client, question_id):
    url = '/ask/{}/100/'.format(question_id)
    return check_get(client, url)


# TODO: avoid passing client to all functions
def answer_question(client, question_id, is_correct):
    ask_question(client, question_id)
    question = models.Question.query.get(question_id)
    url = '/answer/{}/{:d}/100/'.format(question_id, get_answer(question, is_correct).id)
    return check_post(client, url)


def test_ask_without_seed(paul):
    # TODO: factor out with app.new_test_client, subclass it,
    # TODO: pass user (e.g PAUL) to its __init__ method and handle seeds etc
    rv = paul.get('/ask/{}/'.format(EASY_Q))
    assert rv.status_code == 302
    assert re.search(matches_any_ask_url(EASY_Q), rv.location)


def test_team_scores(steve, paul, tim):
    answer_question(steve, EASY_Q, is_correct=True)
    assert_team_score('Apple', num_users=1, score_sum=1)

    answer_question(tim, EASY_Q, is_correct=False)
    assert_team_score('Apple', num_users=2, score_sum=1)

    answer_question(paul, EASY_Q, is_correct=True)
    assert_team_score('Apple', num_users=2, score_sum=1)  # paul is not in Apple team
    assert_team_score('Linux', num_users=1, score_sum=1)
    assert_team_score('Hacker News', num_users=1, score_sum=1)

    answer_question(steve, MEDIUM_Q, is_correct=True)
    assert_team_score('Apple', num_users=2, score_sum=3)


def assert_team_score(team, **expected):
    score = {k: int(v) for k, v in redis_store.hgetall('team:{}'.format(team)).viewitems()}
    for key, value in expected.viewitems():
        assert score[key] == value


# execute this test 10 times to thoroughly check random behaviour
@pytest.mark.parametrize('i', range(10))
def test_never_ask_the_same_question_twice_in_a_row(steve, i):
    # we need to answer every question, because otherwise
    # answer_question(steve, EASY_Q, ...) will always redirect to
    # the unanswered question.
    # We want to test that even if every question is answered,
    # then we don't ask the same question twice in row anyway.
    for question in models.Question.query.all():
        answer_question(steve, question.id, is_correct=True)

    rv = answer_question(steve, EASY_Q, is_correct=True)
    # TODO: check that absolute url is correct
    assert re.search(matches_any_ask_url(EASY_Q), rv.location) is None


@pytest.mark.parametrize('rank, num_users, expected_text', [
    (1, 1, 'top 1%'),
    (1, 2, 'top 1%'),
    (2, 2, 'bottom 50%'),
    (1, 3, 'top 1%'),
    (2, 3, 'top 50%'),
    (3, 3, 'bottom 33%'),
])
def test_get_score_text(rank, num_users, expected_text):
    assert get_score_text(rank, num_users) == expected_text
