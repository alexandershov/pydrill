from __future__ import division

from collections import namedtuple
from urlparse import urlparse


class Team(namedtuple('Team', ['name', 'num_players', 'sum_score'])):
    __slots__ = ()

    NAMES = ['Apple', 'Windows', 'Linux', 'Hacker News', 'Reddit']

    @property
    def avg_score(self):
        if not self.num_players:
            return 0.0
        return self.sum_score / self.num_players


_NAME_BY_PLATFORM = {
    'iphone': 'Apple',
    'ipad': 'Apple',
    'macos': 'Apple',
    'windows': 'Windows',
    'android': 'Linux',
    'linux': 'Linux',
}

_NAME_BY_HOST = {
    'news.ycombinator.com': 'Hacker News',
    'www.reddit.com': 'Reddit',
}


def get_team_names(request):
    names = []
    if request.user_agent.platform in _NAME_BY_PLATFORM:
        names.append(_NAME_BY_PLATFORM[request.user_agent.platform])
    if request.referrer is not None:
        host = urlparse(request.referrer).host
        if host in _NAME_BY_HOST:
            names.append(_NAME_BY_HOST[host])
    return names
