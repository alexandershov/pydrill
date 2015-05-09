from flask import g, render_template, request, session

from pydrill.app import app
from pydrill import utils


@app.route('/q/')
def question():
    app.logger.debug('session = {!r}'.format(session))
    return render_template('question.html')


@app.before_request
def set_user():
    if 'user' not in session:
        g.user = utils.create(request)
    else:
        g.user = utils.User(**session['user'])


@app.after_request
def save_user(response):
    session['user'] = utils.user_as_dict(g.user)
    return response
