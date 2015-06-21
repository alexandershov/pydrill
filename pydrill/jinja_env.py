from __future__ import division

from textwrap import dedent
import random

from flask import render_template_string, g, render_template, session
from jinja2 import Markup
from pygments.formatters.html import HtmlFormatter
from pygments.lexers import get_lexer_by_name
import pygments

from pydrill import app
from pydrill import gen


@app.template_filter()
def render_question(question):
    return Markup(render_template(
        'question.html', question=question, vars=get_template_vars(question)))


@app.template_filter()
def render_explained_question(question, given_answer):
    return Markup(render_template(
        'explained_question.html', question=question, given_answer=given_answer,
        vars=get_template_vars(question)
    ))


def get_template_vars(question):
    template = app.jinja_env.from_string(question.text)
    random.seed(g.seed)
    return vars(template.module)


@app.template_filter()
def render(template, vars={}):
    random.seed(g.seed)
    return Markup(render_template_string(template, **vars))


@app.template_filter()
def in_random_order(iterable):
    items = list(iterable)
    random.shuffle(items)
    return items


def highlight_with_css_class(s, language, css_class):
    formatter = HtmlFormatter(cssclass=css_class)
    # TODO: can we do without strip?
    return pygments.highlight(dedent(unicode(s)), get_lexer_by_name(language),
                              formatter).strip()


@app.template_filter()
def highlight(s, language='python'):
    return highlight_with_css_class(s, language, 'highlight')


@app.template_filter()
def highlight_inline(s, language='python'):
    return highlight_with_css_class(s, language, 'highlight-inline')


@app.template_filter()
def get_answer_message(answer_is_correct):
    if answer_is_correct:
        return 'right!'
    return 'wrong!'


@app.template_filter('repr')
def repr_filter(obj):
    return repr(obj)


@app.template_filter()
def get_score_text(rank, total):
    num_better = rank - 1
    num_worse = total - rank
    if not num_better:
        return 'top 1%'
    if num_worse > num_better:
        return 'top {:.0%}'.format(1 - num_worse / total)
    elif num_better == num_worse:
        return 'top 50%'
    else:
        return 'bottom {:.0%}'.format(1 - num_better / total)


@app.template_global()
def get_prev_answer():
    return session.pop('prev_answer', None)


app.jinja_env.globals.update(gen=gen)
