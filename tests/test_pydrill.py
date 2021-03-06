from functools import wraps
import os
import random
import re

import pytest
from flask.testing import FlaskClient
from flask import session

os.environ['PYDRILL_CONFIG'] = os.path.join(os.path.dirname(__file__), 'pydrill.cfg')
from pydrill import app, db, redis_store
from pydrill import models
from pydrill.jinja_env import get_score_text
from pydrill.utils import User, TEAM_APPLE, TEAM_HN, TEAM_LINUX

EASY_Q = 'average'
MEDIUM_Q = 'static-decorator'
HARD_Q = 'mro'

REFERER = 'HTTP_REFERER'
USER_AGENT = 'HTTP_USER_AGENT'

MAC_USER_AGENT = ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 '
                  '(KHTML, like Gecko) Chrome/41.0.2227.1 Safari/537.36')

LINUX_USER_AGENT = ('Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 '
                    '(KHTML, like Gecko) Chrome/41.0.2227.0 Safari/537.36')


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

    def checked_get(self, path):
        rv = self.get(path)
        assert rv.status_code == 200
        return rv

    def post(self, *args, **kwargs):
        return super(Client, self).post(*args, environ_base=self.__environ_base, **kwargs)

    def checked_post(self, path):
        rv = self.post(path)
        assert rv.status_code == 302
        return rv

    def ask_me(self, question_id):
        path = make_path('ask', question_id)
        return self.checked_get(path)

    def ask_me_without_seed(self, question_id):
        path = make_path_without_seed('ask', question_id)
        return self.get(path)

    def explain_to_me(self, question_id):
        question = models.Question.query.get(question_id)
        path = make_path('explain', question_id, get_any_answer(question).id)
        return self.checked_get(path)

    def answer(self, question_id, is_correct=None):
        if is_correct is None:
            is_correct = random_boolean()
        self.ask_me(question_id)
        question = models.Question.query.get(question_id)
        path = make_path('answer', question_id, get_answer(question, is_correct).id)
        return self.checked_post(path)

    def answer_correct(self, question_id):
        return self.answer(question_id, is_correct=True)

    def answer_wrong(self, question_id):
        return self.answer(question_id, is_correct=False)

    def score(self):
        return self.checked_get('/score/')


def make_path(*path_parts):
    with_seed = path_parts + (random.randint(1, 100),)
    return make_path_without_seed(*with_seed)


def make_path_without_seed(*path_parts):
    return '/'.join([''] + map(str, path_parts) + [''])


@pytest.fixture(autouse=True)
def flush_redis_db():
    redis_store.flushdb()


# this fixture runs once
@pytest.fixture(autouse=True, scope='session')
def create_sql_db():
    db.drop_all()
    db.create_all()
    questions_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'questions')
    for question in [EASY_Q, MEDIUM_Q, HARD_Q]:
        models.read_question(os.path.join(questions_dir, question + '.yml'))
    db.session.commit()


@pytest.fixture(autouse=True)
def run_app_in_testing_mode():
    app.config['TESTING'] = True


def client_fixture(fn):
    """
    :param fn: callable returning test client
    """

    @pytest.yield_fixture
    @wraps(fn)
    def yielding_fn():
        with fn() as client:
            yield client

    return yielding_fn


@client_fixture
def steve():
    return new_test_client({USER_AGENT: MAC_USER_AGENT,
                            REFERER: 'parse this'})


@client_fixture
def paul():
    return new_test_client({USER_AGENT: LINUX_USER_AGENT,
                            REFERER: 'https://news.ycombinator.com/item?id=test'})


@client_fixture
def tim():
    return new_test_client({USER_AGENT: MAC_USER_AGENT})


def get_user():
    return User(**session['user'])


def test_user_id(paul):
    paul.ask_me(EASY_Q)
    user = get_user()
    assert len(user.id) == 36  # length of str(uuid4) is 36
    paul.ask_me(EASY_Q)
    # id doesn't change after the first visit
    assert get_user().id == user.id


def test_new_user_score(paul):
    paul.ask_me(EASY_Q)
    assert get_user().score == 0


def test_user_teams(paul):
    paul.ask_me(EASY_Q)
    assert_same_items(get_user().teams, [TEAM_LINUX, TEAM_HN])


def test_questions():
    assert models.Question.query.count() == 3


def test_only_first_answer_can_increase_score(steve):
    steve.answer_wrong(EASY_Q)
    steve.answer_correct(EASY_Q)
    assert_team_score(TEAM_APPLE, score_sum=0)


def test_cant_increase_score_twice(steve):
    steve.answer_correct(EASY_Q)
    assert_team_score(TEAM_APPLE, score_sum=1)
    steve.answer_correct(EASY_Q)
    assert_team_score(TEAM_APPLE, score_sum=1)


def matches_any_ask_path(*question_ids):
    parts = [r'/ask/{}/(\d+)/$'.format(q) for q in question_ids]
    return '|'.join(parts)


def test_answer_redirects(steve):
    rv = steve.answer(EASY_Q)
    assert redirects_to_question(rv, MEDIUM_Q) or redirects_to_question(rv, HARD_Q)
    rv = steve.answer(MEDIUM_Q)
    assert redirects_to_question(rv, HARD_Q)


def redirects_to_question(rv, question_id):
    regex = matches_any_ask_path(question_id)
    return re.search(regex, rv.location)


def random_boolean():
    return random.choice([True, False])


def assert_same_items(xs, ys):
    assert sorted(xs) == sorted(ys)


def get_answer(question, is_correct):
    return question.answers.filter_by(is_correct=is_correct).first()


def get_any_answer(question):
    answers = list(question.answers)
    return random.choice(answers)


def get_correct_answer(question):
    return get_answer(question, is_correct=True)


def test_ask_without_seed(paul):
    rv = paul.ask_me_without_seed(EASY_Q)
    assert rv.status_code == 302
    assert redirects_to_question(rv, EASY_Q)


def test_team_scores(steve, paul, tim):
    steve.answer_correct(EASY_Q)
    assert_team_score(TEAM_APPLE, num_users=1, score_sum=1)

    tim.answer_wrong(EASY_Q)
    assert_team_score(TEAM_APPLE, num_users=2, score_sum=1)

    paul.answer_correct(EASY_Q)
    assert_team_score(TEAM_APPLE, num_users=2, score_sum=1)  # paul is not in Apple team
    assert_team_score(TEAM_LINUX, num_users=1, score_sum=1)
    assert_team_score(TEAM_HN, num_users=1, score_sum=1)

    steve.answer_correct(MEDIUM_Q)
    assert_team_score(TEAM_APPLE, num_users=2, score_sum=3)


def assert_team_score(team, **expected):
    team_score = redis_store.hgetall('team:{}'.format(team))
    score = {k: int(v) for k, v in team_score.viewitems()}
    for key, value in expected.viewitems():
        assert score[key] == value


def test_never_ask_the_same_question_twice_in_a_row(steve):
    # we need to answer every question, because otherwise
    # steve.answer(EASY_Q) will always redirect to the unanswered question.
    # We want to test that even if every question is answered,
    # then we don't ask the same question twice in row anyway.
    for question in models.Question.query.all():
        steve.answer(question.id)

    rv = steve.answer(EASY_Q)
    assert not redirects_to_question(rv, EASY_Q)


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


def test_ask_question_rendering(steve):
    rv = steve.ask_me(EASY_Q)
    # checking that  '... / 2' is highlighted
    assert '<span class="o">/</span> <span class="mi">2</span>' in rv.data


def test_explain_question_rendering(steve):
    rv = steve.explain_to_me(EASY_Q)
    assert '__future__' in rv.data  # 'from __future__ import division' part


def test_score_rendering(steve):
    steve.answer_correct(EASY_Q)
    rv = steve.score()
    assert_has_score(rv, 1)
    assert '{} is your team'.format(TEAM_APPLE) in rv.data


def test_score_top_text(steve, paul):
    steve.answer_correct(EASY_Q)
    assert "You're in the top 1%" in steve.score().data

    paul.answer_correct(MEDIUM_Q)
    assert "You're in the top 1%" in paul.score().data
    assert "You're in the bottom 50%" in steve.score().data


def test_score_during_ask(steve):
    rv = steve.ask_me(EASY_Q)
    assert_has_score(rv, 0)


# TODO: don't test markup with string comparisons, use css selectors
def assert_has_score(rv, expected_score):
    assert 'score: <strong>{:d}</strong>'.format(expected_score) in rv.data.lower()
