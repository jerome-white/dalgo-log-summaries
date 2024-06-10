import os
import csv
import gzip
import json
import random
import functools as ft
from pathlib import Path
from datetime import datetime
from tempfile import NamedTemporaryFile

import markdown
import flask as fl
import pandas as pd
from flask_httpauth import HTTPBasicAuth

# from mylib import Logger

app = fl.Flask(__name__)
auth = HTTPBasicAuth()

@ft.cache
def dropdown(prompt):
    opts = []
    options = {
        '': 'Select an option',
	1: 'Incorrect',
        2: 'Decent',
        3: 'Correct',
        4: 'Unsure',
    }

    for (k, v) in options.items():
        extra = '' if k else ' selected disabled hidden'
        opts.append(f'<option value="{v.lower()}"{extra}>{v}</option>')

    return '\n'.join([
        f'<select name="s_{prompt}">',
        *opts,
        '</select>',
    ])

def responses(data):
    p_key = 'prompt'

    for (i, d) in enumerate(data['dialogue']):
        prompt = d[p_key]
        response = markdown.markdown(d['response'])
        yield {
            p_key: prompt,
            'response': response,
            'judgement': dropdown(i),
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
        'output',
        'storage',
        'summaries',
    )

    for i in keys:
        value = os.getenv('DALGO_{}'.format(i.upper()))
        yield (i, Path(value))

def q_args(q_string):
    data = load(q_string['summary']).get('dialogue')
    static = {
        'date': datetime.now().strftime('%c'),
        'log': q_string['log'],
    }

    for (k, v) in q_string.items():
        if k.startswith('s_'):
            (_, key) = k.split('_')
            prompt = data[int(key)]['prompt']
            yield dict(static, prompt=prompt, judgement=v)

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

    summary_file = random.choice(summaries(dalgo_vars['summaries']))
    summary_data = load(summary_file)
    event = Path(summary_data['log']).relative_to(dalgo_vars['storage'])
    log_data = dalgo_vars['logs'].joinpath(event)

    if fl.request.args:
        writer = None
        with NamedTemporaryFile(mode='w',
                                suffix='.csv',
                                prefix='',
                                dir=dalgo_vars['output'],
                                delete=False) as fp:
            for i in q_args(fl.request.args):
                if writer is None:
                    writer = csv.DictWriter(fp, fieldnames=i)
                    writer.writeheader()
                writer.writerow(i)

    return fl.render_template(
        'base.html',
        name=event,
        summary=summary_file,
        log=pd.read_json(log_data).to_html(),
        responses=responses(summary_data),
    )

if __name__ == '__main__':
    app.run(debug=True, port=12000)
