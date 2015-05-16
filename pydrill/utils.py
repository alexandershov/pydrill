from __future__ import division

from collections import namedtuple
import random
from urlparse import urlparse
import uuid

from flask import g, render_template
from pydrill import app
from pydrill import redis_store


def render_question(question, **context):
    return render_template('question.html', question=question, vars=get_template_vars(question),
                           **context)


def get_template_vars(question):
    template = app.jinja_env.from_string(question.text)
    random.seed(g.seed)
    return vars(template.module)


class User(object):
    def __init__(self, id=None, score=0, teams=None, answered=None):
        self.id = id or str(uuid.uuid4())
        self.score = score  # TODO: rename to score_sum? or rename Team.score_sum to Team.score?
        self.teams = teams or []
        self.answered = set(answered or [])  # TODO: better name?

    @property
    def avg_score(self):
        return safe_div(self.score, len(self.answered))


def get_user_score():
    # `... + 1` is to convert from zero-indexing to one-indexing
    rank = (redis_store.zrevrank('user_scores', g.user.id) or 0) + 1
    return UserScore(score=g.user.score,
                     rank=rank)


UserScore = namedtuple('UserScore', ['score', 'rank'])


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


def get_team_scores(teams=TEAMS):
    team_scores = []
    for team in teams:
        # TODO: use redis pipelining
        attrs = {'num_users': '0', 'score_sum': '0'}
        attrs.update(redis_store.hgetall(get_team_key(team)))
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
