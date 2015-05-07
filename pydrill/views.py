from flask import render_template, request, session

from pydrill.app import app
from pydrill import score
from pydrill import user


@app.route('/q/')
def question():
    if 'user' not in session:
        session['user'] = user.create(request)
    app.logger.debug('session = {!r}'.format(session))
    app.logger.debug('rank = {!r}'.format(score.get_rank(user.User(*session['user']))))
    return render_template('question.html')
