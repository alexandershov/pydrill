from random import SystemRandom

from flask import g, redirect, render_template, request, session, url_for
from sqlalchemy import func

from pydrill import app, redis_store
from pydrill import utils
from pydrill.models import Answer, Question

urandom = SystemRandom()


@app.route('/')
def ask_next_question():
    return ask_question()


def ask_question(question_id=None):
    if question_id is None:
        question_id = get_next_question().id
    return redirect(url_for('ask', question_id=question_id, seed=make_seed()))


@app.route('/ask/<question_id>/')
def ask_with_random_seed(question_id):
    return ask_question(question_id)


@app.route('/ask/<question_id>/<seed>/')
def ask(question_id, seed):
    question = get_question(question_id)
    g.user.ask(question)
    return render_template('ask.html', question=question)


@app.route('/answer/<question_id>/<answer_id>/<seed>/', methods=['POST'])
def accept_answer(question_id, answer_id, seed):
    question, answer = get_question_and_answer(question_id, answer_id)
    g.user.answer(question, answer)
    remember_answer(answer)
    return ask_question()


def remember_answer(answer):
    explain_url = url_for('explain', question_id=answer.question.id, answer_id=answer.id,
                          seed=g.seed)
    session['prev_answer'] = {'is_correct': answer.is_correct,
                              'explain_url': explain_url}


@app.route('/score/')
def show_score():
    return render_template('score.html', teams_scores=utils.get_teams_scores())


@app.route('/explain/<question_id>/<answer_id>/<seed>/')
def explain(question_id, answer_id, seed):
    question, given_answer = get_question_and_answer(question_id, answer_id)
    return render_template('explain.html', question=question, given_answer=given_answer)


@app.before_request
def set_globals():
    if request.view_args is None:
        # no matching rule
        return
    # setting g.redis_pipeline first because it's used by utils.create_user
    g.redis_pipeline = redis_store.pipeline(transaction=False)
    g.seed = request.view_args.get('seed')
    if 'user' not in session:
        g.user = utils.User.create(teams=utils.get_cur_teams())
    else:
        g.user = utils.User(**session['user'])
    g.num_users = redis_store.zcard('user_scores')


@app.after_request
def save_user_and_execute_redis_pipeline(response):
    if request.view_args is None:
        # no matching rule
        return response
    session['user'] = g.user.as_dict()
    g.redis_pipeline.execute()
    return response


def get_next_question():
    distance_to_user_avg_score = func.abs(Question.difficulty - g.user.avg_score)
    question = (Question.query
                .filter(~Question.id.in_(g.user.answered_questions)
                        & (Question.id != g.user.last_question))
                .order_by(distance_to_user_avg_score)
                .first())
    if question is None:
        # user answered every question, just give them a random one that preferably is
        # not the last asked question
        question = Question.query.order_by(Question.id == g.user.last_question,
                                           func.random()).first()
    return question


def get_question(question_id):
    return Question.query.get(question_id)


def get_answer(question_id, answer_id):
    return Answer.query.get((answer_id, question_id))


def get_question_and_answer(question_id, answer_id):
    return get_question(question_id), get_answer(question_id, answer_id)


def make_seed():
    return urandom.randint(1, 999)
