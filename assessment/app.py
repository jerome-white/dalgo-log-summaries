import os
# import csv
import gzip
import json
import string
import random
import functools as ft
from pathlib import Path
from dataclasses import dataclass
# from tempfile import NamedTemporaryFile

import flask as fl
import pandas as pd
import markdown
from flask_httpauth import HTTPBasicAuth

from mylib import Logger

app = fl.Flask(__name__)
auth = HTTPBasicAuth()

@ft.cache
def whitespacing():
    ws = {
        ' ': ' ',
        '\t': '&nbsp;' * 5,
    }
    for i in string.whitespace:
        ws.setdefault(i, '<br>')

    return ws

def to_html(text):
    for i in whitespacing().items():
        text = text.replace(*i)

    return text

@ft.cache
def dropdown(name):
    options = {
        '': 'Select an option',
        1: 'Incorrect',
        2: 'Decent',
        3: 'Correct',
        4: 'Unsure',
    }

    opts = []
    for (k, v) in options.items():
        extra = '' if k else ' selected disabled hidden'
        opts.append(f'<option value="{k}"{extra}>{v}</option>')

    return '\n'.join([
        f'<select name="{name}">',
        *opts,
        '</select>',
    ])

def responses(data):
    drop = dropdown(data['log'])
    prompt = 'prompt'

    for i in data['dialogue']:
        response = markdown.markdown(i['response'])
        yield {
            prompt: i[prompt],
            'response': response,
            'judgement': drop,
        }

@ft.cache
def summaries(path):
    return list(path.rglob('*.json.gz'))

def load(summary):
    with gzip.open(summary, 'r') as fp:
        data = fp.read().decode('utf-8')

    return json.loads(data)

def environ():
    keys = (
        'logs',
        'summaries',
        'storage',
    )

    for i in keys:
        value = os.getenv('DALGO_{}'.format(i.upper()))
        yield (i, Path(value))

#
#
#
@auth.verify_password
def verify_password(username, password):
    params = (
        ('username', username),
        ('password', password),
    )

    return all(os.getenv(f'DALGO_{x.upper()}') == y for (x, y) in params)

@app.route('/')
@auth.login_required
def index():
    dalgo_vars = dict(environ())
    summary_data = load(random.choice(summaries(dalgo_vars['summaries'])))
    event = Path(summary_data['log']).relative_to(dalgo_vars['storage'])
    log_data = dalgo_vars['logs'].joinpath(event)

    return fl.render_template(
        'base.html',
        name=event,
        log=pd.read_json(log_data).to_html(),
        responses=responses(summary_data),
    )

if __name__ == '__main__':
    app.run(debug=True, port=12000)
