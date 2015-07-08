from flask.ext.script import Manager

from pydrill import app, db
from pydrill import models


manager = Manager(app)


@manager.command
def load_questions(directory):
    """Replace current set of questions with questions from the specified directory."""
    for model in [models.Answer, models.Question]:
        model.query.delete()
    models.load_questions(directory)
    db.session.commit()  # models.load_questions() commits itself, but better be explicit


if __name__ == '__main__':
    manager.run()
