from __future__ import division

from collections import namedtuple
from urlparse import urlparse
import uuid

from flask import g, request

from pydrill import redis_store


class User(object):
    def __init__(self, id=None, score=0, teams=None, answered_questions=None):
        self.id = id or str(uuid.uuid4())
        self.score = score
        self.teams = teams or []
        self.answered_questions = set(answered_questions or [])

    @property
    def avg_score(self):
        return safe_div(self.score, len(self.answered_questions))

    @property
    def rank(self):
        # `... + 1` is to convert from zero-indexing to one-indexing
        return (redis_store.zrevrank('user_scores', self.id) or 0) + 1

    def answer(self, question, answer):
        if answer.is_correct and question.id not in self.answered_questions:
            add_score(self, question.difficulty)
        self.answered_questions.add(question.id)


def create_user():
    user = User(teams=get_cur_teams())
    init_user_score(user)
    return user


def user_as_dict(user):
    return {'id': user.id, 'score': user.score, 'teams': user.teams,
            'answered_questions': list(user.answered_questions)}  # set is not JSON serializable


_TEAM_BY_PLATFORM = {
    'iphone': 'Apple',
    'ipad': 'Apple',
    'macos': 'Apple',
    'windows': 'Windows',
    'android': 'Linux',
    'linux': 'Linux',
}

_TEAM_BY_REFERRER = {
    'news.ycombinator.com': 'Hacker News',
    'www.reddit.com': 'Reddit',
}

TEAMS = ['Apple', 'Windows', 'Linux', 'Hacker News', 'Reddit']


def get_cur_teams():
    teams = []
    platform = request.user_agent.platform
    if platform in _TEAM_BY_PLATFORM:
        teams.append(_TEAM_BY_PLATFORM[platform])

    if request.referrer is not None:
        hostname = urlparse(request.referrer).hostname
        if hostname in _TEAM_BY_REFERRER:
            teams.append(_TEAM_BY_REFERRER[hostname])
    return teams


def get_team_scores(teams=TEAMS):
    team_scores = []
    p = redis_store.pipeline(transaction=False)
    for team in teams:
        p.hgetall(get_team_key(team))
    team_dicts = p.execute()
    for team, attrs in zip(teams, team_dicts):
        attrs.setdefault('num_users', '0')
        attrs.setdefault('score_sum', '0')
        typed_attrs = {name: int(value) for name, value in attrs.viewitems()}
        team_scores.append(TeamScore(team=team, **typed_attrs))
    return sorted(team_scores, key=lambda ts: ts.avg_score, reverse=True)


def get_team_key(name):
    return 'team:{}'.format(name)


def init_user_score(user):
    add_score(user, 0)
    for team in user.teams:
        g.redis_pipeline.hincrby(get_team_key(team), 'num_users', 1)


def add_score(user, delta):
    user.score += delta
    g.redis_pipeline.zincrby('user_scores', user.id, delta)
    for team in user.teams:
        g.redis_pipeline.hincrby(get_team_key(team), 'score_sum', delta)


def get_rank(user):
    return redis_store.zrevrank('user_scores', user.id)


class TeamScore(namedtuple('TeamScore', ['team', 'num_users', 'score_sum'])):
    __slots__ = ()

    @property
    def avg_score(self):
        return safe_div(self.score_sum, self.num_users)


def safe_div(x, y):
    if y == 0:
        return 0
    return x / y
