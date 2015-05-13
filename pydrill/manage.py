from flask.ext.script import Manager

from pydrill import app
from pydrill import models


manager = Manager(app)


@manager.command
def load_questions(directory):
    """Delete current set of questions
    load questions from the specified directory.
    """
    models.Answer.query.delete()
    models.Question.query.delete()
    models.load_questions(directory)


if __name__ == '__main__':
    manager.run()
