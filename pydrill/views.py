from flask import render_template
from pydrill.app import app


@app.route('/q/')
def question():
    return render_template('question.html')
