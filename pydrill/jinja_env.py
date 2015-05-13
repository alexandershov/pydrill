import random
from textwrap import dedent
from flask import render_template_string, g
from pygments.formatters.html import HtmlFormatter
from pygments.lexers import get_lexer_by_name
import pygments
from jinja2 import Markup
from pydrill import app
from pydrill import gen


def render(template, vars={}):
    random.seed(g.seed)
    return Markup(render_template_string(template, **vars))


@app.template_filter('highlight')
def highlight(s, language='python'):
    formatter = HtmlFormatter(cssclass='highlight')
    # TODO: can we do without strip?
    return pygments.highlight(dedent(unicode(s)), get_lexer_by_name(language),
                              formatter).strip()


app.jinja_env.globals.update(gen=gen, render=render)
