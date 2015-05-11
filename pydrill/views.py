from random import SystemRandom
from flask import g, redirect, render_template, request, session, url_for
from sqlalchemy import func

from werkzeug.routing import BaseConverter

from pydrill import app, db, redis_store
from pydrill import utils
from pydrill.models import Answer, Question


urandom = SystemRandom()


class ModelConverter(BaseConverter):
    model = None  # redefine it in subclasses

    def to_python(self, value):
        return self.model.query.get(value)

    def to_url(self, value):
        return value.id


class QuestionConverter(ModelConverter):
    model = Question


class AnswerConverter(ModelConverter):
    model = Answer


app.url_map.converters['Question'] = QuestionConverter
app.url_map.converters['Answer'] = AnswerConverter


@app.route('/ask/<Question:question>/')
def ask_question_with_random_seed(question):
    return redirect(url_for('ask_question', question=question, seed=make_seed()))


@app.route('/ask/<Question:question>/<seed>/')
def ask_question(question, seed):
    # TODO: figure out how to avoid db.session and make ModelConverter to work with lazy='dynamic'
    db.session.add(question)
    app.logger.debug('session = {!r}, question = {!r}'.format(session, question))
    return render_template('question.html')


@app.route('/answer/<Question:question>/<Answer:answer>/<seed>/', methods=['POST'])
def accept_answer(question, answer, seed):
    # TODO: figure out how to avoid db.session and make ModelConverter to work with lazy='dynamic'
    db.session.add(question)
    db.session.add(answer)
    assert answer.question == question
    if answer.is_correct and question.id not in g.user.answered:
        utils.add_score(g.user, question.difficulty)
    g.user.answered.add(question.id)
    return redirect(url_for('ask_question', question=get_next_question(), seed=make_seed()))


@app.before_request
def set_globals():
    # set g.redis_pipeline first because it's used by utils.create_user
    g.redis_pipeline = redis_store.pipeline()
    if 'user' not in session:
        g.user = utils.create_user(request)
    else:
        g.user = utils.User(**session['user'])


@app.after_request
def execute_redis_pipeline(response):
    session['user'] = utils.user_as_dict(g.user)
    g.redis_pipeline.execute()
    return response


# FIXME: find out how to see error messages during testing and remove this handler
@app.errorhandler(500)
def internal_error(error):
    import traceback
    import sys

    traceback.print_exception(*sys.exc_info())
    return 'Internal Error', 500


# TODO: use user score to find the suitable (by difficulty) question
def get_next_question():
    question = (Question.query
                .filter(~Question.id.in_(g.user.answered))
                .order_by(func.random())
                .first())
    if question is None:  # user answered every question, just give them a random one
        question = Question.query.order_by(func.random()).first()
    return question


def make_seed():
    return urandom.randint(1, 999)
