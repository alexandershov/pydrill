from glob import glob
import os
import yaml
from pydrill.app import db


class Question(db.Model):
    __tablename__ = 'questions'

    id = db.Column(db.Text, primary_key=True)
    text = db.Column(db.Text, nullable=False)
    explanation = db.Column(db.Text, nullable=False)
    difficulty = db.Column(db.Integer, nullable=False)
    answers = db.relationship('Answer', backref='question', lazy='dynamic')


class Answer(db.Model):
    __tablename__ = 'answers'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    text = db.Column(db.Text, nullable=False)
    is_correct = db.Column(db.Boolean, nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey(Question.id), nullable=False)


def load_questions(directory):
    question_paths = glob(os.path.join(directory, '*.yml'))
    if not question_paths:
        raise ValueError('directory {} doesn\'t have any .yml files'.format(directory))
    for path in question_paths:
        with open(path) as stream:
            question_dict = yaml.load(stream)
            answer_dicts = question_dict.pop('answers')
            question_id = os.path.splitext(os.path.basename(path))[0]
            question = Question(id=question_id, **question_dict)
            db.session.add(question)
            for answer_dict in answer_dicts:
                answer = Answer(question_id=question_id, **answer_dict)
                db.session.add(answer)
    db.session.commit()
