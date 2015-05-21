from random import SystemRandom

from flask import g, redirect, render_template, request, session, url_for
from sqlalchemy import func

from pydrill import app, redis_store
from pydrill import utils
from pydrill.models import Answer, Question

urandom = SystemRandom()


@app.route('/ask/<question_id>/')
def ask_with_random_seed(question_id):
    return redirect(url_for('ask', question_id=question_id, seed=make_seed()))


@app.route('/ask/<question_id>/<seed>/')
def ask(question_id, seed):
    return render_template('ask.html', question=get_cur_question())


@app.route('/answer/<question_id>/<answer_id>/<seed>/', methods=['POST'])
def accept_answer(question_id, answer_id, seed):
    question, answer = get_cur_question_and_answer()
    g.user.answer(question, answer)
    remember_answer(answer)
    return redirect(url_for('ask', question_id=get_next_question().id, seed=make_seed()))


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
    question, given_answer = get_cur_question_and_answer()
    return render_template('explain.html', question=question, given_answer=given_answer)


@app.before_request
def set_globals():
    # setting g.redis_pipeline first because it's used by utils.create_user
    g.redis_pipeline = redis_store.pipeline(transaction=False)
    g.seed = request.view_args.get('seed')
    if 'user' not in session:
        g.user = utils.User.create(teams=utils.get_cur_teams())
    else:
        g.user = utils.User(**session['user'])


@app.after_request
def save_user_and_execute_redis_pipeline(response):
    session['user'] = utils.user_as_dict(g.user)
    g.redis_pipeline.execute()
    return response


def get_next_question():
    distance_to_user_avg_score = func.abs(Question.difficulty - g.user.avg_score)
    question = (Question.query
                .filter(~Question.id.in_(g.user.answered_questions))
                .order_by(distance_to_user_avg_score)
                .first())
    if question is None:
        # user answered every question, just give them a random one
        question = Question.query.order_by(func.random()).first()
    return question


def get_cur_question():
    return Question.query.get(request.view_args['question_id'])


def get_cur_answer():
    return Answer.query.get(request.view_args['answer_id'])


def get_cur_question_and_answer():
    question = get_cur_question()
    answer = get_cur_answer()
    assert answer.question == question
    return question, answer


def make_seed():
    return urandom.randint(1, 999)
