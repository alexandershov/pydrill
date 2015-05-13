import random
from flask import render_template_string, g
from pydrill import app
from pydrill import gen


def render(template, vars={}):
    random.seed(g.seed)
    return render_template_string(template, **vars)


app.jinja_env.globals.update(gen=gen, render=render)
