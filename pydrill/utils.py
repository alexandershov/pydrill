from __future__ import division

from collections import namedtuple
from urlparse import urlparse
import uuid

from flask import g, request

from pydrill import redis_store


class User(object):
    @classmethod
    def create(cls, *args, **kwargs):
        user = cls(*args, **kwargs)
        init_user_score(user)
        return user

    def __init__(self, id=None, score=0, teams=None, last_question=None, answered_questions=None):
        self.id = id or str(uuid.uuid4())
        self.score = score
        self.teams = teams or []
        self.last_question = last_question
        self.answered_questions = set(answered_questions or [])

    @property
    def avg_score(self):
        return safe_div(self.score, len(self.answered_questions))

    @property
    def rank(self):
        # converting to one-based indexing
        return redis_store.zrevrank('user_scores', self.id) + 1

    @property
    def percentile(self):
        return 1 - safe_div(self.rank, redis_store.zcard('user_scores'))

    def answer(self, question, answer):
        self.last_question = question.id
        if answer.is_correct and question.id not in self.answered_questions:
            add_score(self, question.difficulty)
        self.answered_questions.add(question.id)


def user_as_dict(user):
    return {'id': user.id, 'score': user.score, 'teams': user.teams,
            'last_question': user.last_question,
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


def get_teams_scores(teams=TEAMS):
    teams_scores = []
    teams_attrs = hgetall_many(map(get_team_key, teams))
    for team, attrs in zip(teams, teams_attrs):
        teams_scores.append(TeamScore(team=team,
                                      num_users=int(attrs.get('num_users', 0)),
                                      score_sum=int(attrs.get('score_sum', 0))))
    return sorted(teams_scores, key=lambda ts: ts.score, reverse=True)


def hgetall_many(keys):
    p = redis_store.pipeline(transaction=False)
    for key in keys:
        p.hgetall(key)
    return p.execute()


def get_team_key(team):
    return 'team:{}'.format(team)


def init_user_score(user):
    add_score(user, 0)
    for team in user.teams:
        g.redis_pipeline.hincrby(get_team_key(team), 'num_users', 1)


def add_score(user, delta):
    user.score += delta
    g.redis_pipeline.zincrby('user_scores', user.id, delta)
    for team in user.teams:
        g.redis_pipeline.hincrby(get_team_key(team), 'score_sum', delta)
    g.redis_pipeline.execute()


# TODO: create and use Team class instead
class TeamScore(namedtuple('TeamScore', ['team', 'num_users', 'score_sum'])):
    __slots__ = ()

    @property
    def score(self):
        return safe_div(self.score_sum, self.num_users)


def safe_div(x, y):
    if y == 0:
        return 0
    return x / y
