import random
from textwrap import dedent
from flask import render_template_string, g
from pygments.formatters.html import HtmlFormatter
from pygments.lexers import get_lexer_by_name
import pygments
from jinja2 import Markup
from pydrill import app
from pydrill import gen


@app.template_filter('render')
def render(template, vars={}):
    random.seed(g.seed)
    return Markup(render_template_string(template, **vars))


@app.template_filter('in_random_order')
def in_random_order(iterable):
    items = list(iterable)
    random.shuffle(items)
    return items


def highlight_with_css_class(s, language, css_class):
    formatter = HtmlFormatter(cssclass=css_class)
    # TODO: can we do without strip?
    return pygments.highlight(dedent(unicode(s)), get_lexer_by_name(language),
                              formatter).strip()


@app.template_filter('highlight')
def highlight(s, language='python'):
    return highlight_with_css_class(s, language, 'highlight')


@app.template_filter('highlight_inline')
def highlight_inline(s, language='python'):
    return highlight_with_css_class(s, language, 'highlight-inline')


app.jinja_env.globals.update(gen=gen)
