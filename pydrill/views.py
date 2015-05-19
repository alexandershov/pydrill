from random import SystemRandom

from flask import flash, g, redirect, render_template, request, session, url_for
from sqlalchemy import func

from pydrill import app, redis_store
from pydrill import utils
from pydrill.models import Answer, Question

urandom = SystemRandom()


@app.route('/ask/<question_id>/')
def ask_question_with_random_seed(question_id):
    return redirect(url_for('ask_question', question_id=question_id, seed=make_seed()))


@app.route('/ask/<question_id>/<seed>/')
def ask_question(question_id, seed):
    g.seed = seed
    question = Question.query.get(question_id)
    return utils.render_question(question, score=utils.get_user_score(), explain=False)


@app.route('/answer/<question_id>/<answer_id>/<seed>/', methods=['POST'])
def accept_answer(question_id, answer_id, seed):
    question = Question.query.get(question_id)
    answer = Answer.query.get(answer_id)
    assert answer.question == question
    flash({'text': 'right!' if answer.is_correct else 'wrong!',
           'question_id': question_id,
           'answer_id': answer_id,
           'seed': seed,
           'is_correct': answer.is_correct}, 'answer')
    if answer.is_correct and question.id not in g.user.answered:
        utils.add_score(g.user, question.difficulty)
    g.user.answered.add(question.id)
    return redirect(url_for('ask_question', question_id=get_next_question().id, seed=make_seed()))


@app.route('/score/')
def show_score():
    return render_template('score.html', team_scores=utils.get_team_scores(),
                           score=utils.get_user_score())


@app.route('/explain/<question_id>/<answer_id>/<seed>/')
def explain(question_id, answer_id, seed):
    # TODO: DRY it up with ask_question
    g.seed = seed
    question = Question.query.get(question_id)
    given_answer = Answer.query.get(answer_id)
    return utils.render_question(question, score=utils.get_user_score().score,
                                 explain=True, given_answer=given_answer)


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
