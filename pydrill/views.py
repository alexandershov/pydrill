from random import SystemRandom
from flask import g, redirect, request, session, url_for
from sqlalchemy import func

from pydrill import app, redis_store
from pydrill import utils
from pydrill.models import Answer, Question
from pydrill.utils import render_question


urandom = SystemRandom()


@app.route('/ask/<question_id>/')
def ask_question_with_random_seed(question_id):
    return redirect(url_for('ask_question', question_id=question_id, seed=make_seed()))


@app.route('/ask/<question_id>/<seed>/')
def ask_question(question_id, seed):
    g.seed = seed
    question = Question.query.get(question_id)
    app.logger.debug('session = {!r}, question = {!r}'.format(session, question))
    return render_question(question)


@app.route('/answer/<question_id>/<answer_id>/<seed>/', methods=['POST'])
def accept_answer(question_id, answer_id, seed):
    question = Question.query.get(question_id)
    answer = Answer.query.get(answer_id)
    assert answer.question == question
    if answer.is_correct and question.id not in g.user.answered:
        utils.add_score(g.user, question.difficulty)
    g.user.answered.add(question.id)
    return redirect(url_for('ask_question', question_id=get_next_question().id, seed=make_seed()))


@app.before_request
def set_globals():
    # set g.redis_pipeline first because it's used by utils.create_user
    g.redis_pipeline = redis_store.pipeline(transaction=False)
    if 'user' not in session:
        g.user = utils.create_user(request)
    else:
        g.user = utils.User(**session['user'])


@app.after_request
def execute_redis_pipeline(response):
    session['user'] = utils.user_as_dict(g.user)
    g.redis_pipeline.execute()
    return response


def get_next_question():
    question = (Question.query
                .filter(~Question.id.in_(g.user.answered))
                .order_by(func.abs(Question.difficulty - g.user.avg_score))
                .first())
    if question is None:  # user answered every question, just give them a random one
        question = Question.query.order_by(func.random()).first()
    return question


def make_seed():
    return urandom.randint(1, 999)
