import os
import re
from flask.testing import FlaskClient

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


# TODO: switch to app.test_client when Flask 1.0 is ready
def new_test_client(environ_base, *args, **kwargs):
    """Copy-pasted from Flask.test_client because we need to pass environ_base
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
    return new_test_client(STEVE)


@pytest.fixture()
def paul():
    return new_test_client(PAUL)


@pytest.fixture()
def tim():
    return new_test_client(TIM)


def get_user():
    return User(**session['user'])


def test_new_user(paul):
    with paul:
        check_get(paul, '/ask/average/100/')
        user = get_user()
        user_id = user.id
        assert len(user.id) == 36  # length of str(uuid4) is 36
        assert user.score == 0
        assert_same_items(user.teams, ['Linux', 'Hacker News'])

        assert_team_score('Linux', num_users=1, score_sum=0)
        assert_team_score('Hacker News', num_users=1, score_sum=0)

        check_get(paul, '/ask/average/100/')
        # id doesn't change after the first visit
        assert get_user().id == user_id


def test_questions():
    assert models.Question.query.count() == 2


@pytest.mark.parametrize('question_id, are_correct, scores', [
    # only the first correct answer can increase the score
    ('average', [True, True], [1, 1]),
    ('average', [False, True], [0, 0]),
])
# TODO: more specific name
def test_correct_answer(steve, question_id, are_correct, scores):
    assert len(are_correct) == len(scores)
    for is_correct, score in zip(are_correct, scores):
        answer_question(steve, question_id, is_correct=is_correct)
        assert_team_score('Apple', num_users=1, score_sum=score)


@pytest.mark.parametrize('question_ids, redirect_path_re', [
    (['average'], r'/ask/static-decorator/(\d+)/$'),
    (['static-decorator'], r'/ask/average/(\d+)/$'),
    (['average', 'static-decorator'], r'.*'),  # no unanswered question, any path will do
])
def test_answer_redirects(steve, question_ids, redirect_path_re):
    for i, question_id in enumerate(question_ids):
        rv = answer_question(steve, question_id, is_correct=True)
        if i == len(question_ids) - 1:
            # TODO: check that absolute url is correct
            assert re.search(redirect_path_re, rv.location)


STEVE = {'HTTP_USER_AGENT': MAC_USER_AGENT,
         'HTTP_REFERER': 'parse this'}

PAUL = {'HTTP_USER_AGENT': LINUX_USER_AGENT,
        'HTTP_REFERER': 'https://news.ycombinator.com/item?id=test'}

TIM = {'HTTP_USER_AGENT': MAC_USER_AGENT}


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


def get_any_wrong_answer(question):
    return get_answer(question, is_correct=False)


# TODO: avoid passing client to all functions
def answer_question(client, question_id, is_correct):
    question = models.Question.query.get(question_id)
    url = '/answer/{}/{:d}/100/'.format(question_id, get_answer(question, is_correct).id)
    rv = check_post(client, url)
    return rv


def test_ask_without_seed(paul):
    # TODO: factor out with app.new_test_client, subclass it,
    # TODO: pass user (e.g PAUL) to its __init__ method and handle seeds etc
    rv = paul.get('/ask/average/')
    assert rv.status_code == 302
    # TODO: DRY it up with test_answer_redirects
    assert re.search(r'/ask/average/(\d+)/', rv.location)


def test_team_scores(steve, paul, tim):
    answer_question(steve, 'average', is_correct=True)
    assert_team_score('Apple', num_users=1, score_sum=1)

    answer_question(tim, 'average', is_correct=False)
    assert_team_score('Apple', num_users=2, score_sum=1)

    answer_question(paul, 'average', is_correct=True)
    assert_team_score('Apple', num_users=2, score_sum=1)  # paul is not in Apple team
    assert_team_score('Linux', num_users=1, score_sum=1)
    assert_team_score('Hacker News', num_users=1, score_sum=1)

    answer_question(steve, 'static-decorator', is_correct=True)
    assert_team_score('Apple', num_users=2, score_sum=3)


def assert_team_score(team, num_users, score_sum):
    assert (redis_store.hgetall('team:{}'.format(team))
            == {'num_users': str(num_users), 'score_sum': str(score_sum)})
