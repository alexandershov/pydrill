from flask import g, redirect, render_template, request, session, url_for
from sqlalchemy import func

from pydrill.app import app
from pydrill import utils
from pydrill.models import Answer, Question


# TODO: add seeds to urls, so question texts are randomly generated
@app.route('/ask/<question_id>/')
def ask_question(question_id):
    question = Question.query.get(question_id)
    app.logger.debug('session = {!r}, question = {!r}'.format(session, question))
    return render_template('question.html')


@app.route('/answer/<question_id>/<answer_id>/', methods=['POST'])
def accept_answer(question_id, answer_id):
    question = Question.query.get(question_id)
    answer = Answer.query.get(answer_id)
    assert answer.question == question
    if answer.is_correct and question.id not in g.user.answered:
        utils.add_score(g.user, question.difficulty)
    g.user.answered.add(question.id)
    return redirect(url_for('ask_question', question_id=get_next_question().id))


@app.before_request
def set_user():
    if 'user' not in session:
        g.user = utils.create_user(request)
    else:
        g.user = utils.User(**session['user'])


@app.after_request
def save_user(response):
    session['user'] = utils.user_as_dict(g.user)
    return response


# FIXME: find out how to see error messages during testing and remove this handler
@app.errorhandler(500)
def internal_error(error):
    print(error)
    return 'Internal Error', 500


# TODO: use user score to find the suitable (by difficulty) question
def get_next_question():
    return (Question.query
            .filter(~Question.id.in_(g.user.answered))
            .order_by(func.random())
            .first())
