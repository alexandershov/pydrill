from pydrill.app import redis_store
from pydrill.team import Team


# TODO: should it all go to team.py?

def get_teams():
    teams = []
    for name in Team.NAMES:
        team_attrs = redis_store.hgetall(get_team_key(name))
        teams.append(Team(name=name, **team_attrs))
    return teams


def get_team_key(name):
    return 'team:{}'.format(name)


# TODO: fix player/user dualism
def add_player(user):
    change(user, 0)
    for name in user.team_names:
        redis_store.hincrby(get_team_key(name), 'num_players', 1)


def change(user, delta):
    redis_store.zincrby('player_scores', user.id, delta)
    for name in user.team_names:
        redis_store.hincrby(get_team_key(name), 'sum_score', delta)


def get_rank(user):
    return redis_store.zrevrank('player_scores', user.id)
