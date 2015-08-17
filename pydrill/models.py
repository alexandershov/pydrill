from glob import glob
import os
import random

import yaml

from pydrill import db


class Column(db.Column):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('nullable', False)
        super(Column, self).__init__(*args, **kwargs)


class Question(db.Model):
    __tablename__ = 'questions'

    id = Column(db.Text, primary_key=True)
    text = Column(db.Text)
    explanation = Column(db.Text)
    difficulty = Column(db.Integer)
    answers = db.relationship('Answer', backref='question', lazy='dynamic')

    def __repr__(self):
        return 'Question(id={!r})'.format(self.id)


class Answer(db.Model):
    __tablename__ = 'answers'

    id = Column(db.Integer, primary_key=True)
    is_correct = Column(db.Boolean)
    question_id = Column(db.Integer, db.ForeignKey(Question.id), primary_key=True)
    text = Column(db.Text)

    @property
    def is_wrong(self):
        return not self.is_correct

    def __repr__(self):
        return ('Answer(id={self.id!r}, is_correct={self.is_correct!r}, '
                'question={self.question!r})'.format(self=self))


def load_questions(directory):
    question_paths = glob(os.path.join(directory, '*.yml'))
    if not question_paths:
        raise ValueError("directory {} doesn't have any .yml files".format(directory))
    for path in question_paths:
        read_question(path)
    db.session.commit()


def read_question(path):
    question_id = os.path.splitext(os.path.basename(path))[0]
    with open(path) as stream:
        question_attrs = yaml.load(stream)
    answers = question_attrs.pop('answers')
    question = Question(id=question_id, **question_attrs)
    db.session.add(question)
    answer_ids = get_answer_ids(question_id, len(answers))
    for answer_id, answer_attrs in zip(answer_ids, answers):
        answer = Answer(id=answer_id, question_id=question_id, **answer_attrs)
        db.session.add(answer)
    return question


def get_answer_ids(question_id, num_answers):
    """Return answer ids for the given question.
    Ids are randomized so is_correct doesn't always have id==1.
    Randomization always yield the same results for the given question_id.
    """
    ids = list(range(1, num_answers + 1))
    random.seed(hash(question_id))
    random.shuffle(ids)
    return ids
