from __future__ import division

from collections import namedtuple
from urlparse import urlparse
import uuid

from pydrill.app import redis_store


class User(object):
    def __init__(self, id=None, score=0, teams=None, answered=None):
        self.id = id or str(uuid.uuid4())
        self.score = score
        self.teams = teams or []
        self.answered = set(answered or [])  # TODO: better name?


def create_user(request):
    user = User(teams=get_teams(request))
    init_user_score(user)
    return user


def user_as_dict(user):
    return {'id': user.id, 'score': user.score, 'teams': user.teams,
            'answered': list(user.answered)}  # set is not JSON serializable


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


def get_teams(request):
    teams = []
    platform = request.user_agent.platform
    if platform in _TEAM_BY_PLATFORM:
        teams.append(_TEAM_BY_PLATFORM[platform])

    if request.referrer is not None:
        host = urlparse(request.referrer).hostname
        if host in _TEAM_BY_REFERRER:
            teams.append(_TEAM_BY_REFERRER[host])
    return teams


def get_team_scores(teams):
    team_scores = []
    for team in teams:
        attrs = redis_store.hgetall(get_team_key(team))
        team_scores.append(TeamScore(team=team, **attrs))
    return sorted(team_scores, key=lambda ts: ts.avg_score, reverse=True)


def get_team_key(name):
    return 'team:{}'.format(name)


def init_user_score(user):
    add_score(user, 0)
    # TODO: use redis pipelining
    for team in user.teams:
        redis_store.hincrby(get_team_key(team), 'num_users', 1)


def add_score(user, delta):
    user.score += delta
    redis_store.zincrby('user_scores', user.id, delta)
    # TODO: use redis pipelining
    for team in user.teams:
        redis_store.hincrby(get_team_key(team), 'score_sum', delta)


def get_rank(user):
    return redis_store.zrevrank('user_scores', user.id)


class TeamScore(namedtuple('TeamScore', ['team', 'num_users', 'score_sum'])):
    __slots__ = ()

    @property
    def avg_score(self):
        if not self.num_users:
            return 0.0
        return self.score_sum / self.num_users
