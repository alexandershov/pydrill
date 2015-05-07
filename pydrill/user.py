from collections import namedtuple
import uuid

from pydrill import team
from pydrill import score


class User(namedtuple('User', ['id', 'score', 'team_names'])):
    __slots__ = ()

    @classmethod
    def new(cls, request):
        return cls(id=str(uuid.uuid4()), score=0, team_names=team.get_team_names(request))


def create(request):
    user = User.new(request)
    score.add_player(user)
    return user
