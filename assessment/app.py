import os
import gzip
import json
import uuid
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
    html = []
    options = (
	'incorrect',
        'decent',
        'correct',
        'unsure',
    )

    for i in options:
        html.append(f'''
        <input type="radio" id="html" name="p_{prompt}" value="{i}">
        <label for="{i}">{i.capitalize()}</label>
        ''')

    return '&nbsp;'.join(html)

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
        # 'storage',
        'summaries',
    )

    for i in keys:
        value = os.getenv('DALGO_{}'.format(i.upper()))
        yield (i, Path(value))

def extract(q_string):
    data = load(q_string['summary']).get('dialogue')
    for (k, judgement) in q_string.items():
        if k.startswith('p_'): # see the dropdown function
            (_, index) = k.split('_')
            prompt = data[int(index)]['prompt']
            yield {
                'prompt': prompt,
                'judgement': judgement,
            }

def record(data, destination):
    submission = {
        'date': datetime.now().strftime('%c'),
        'annotations': list(extract(data)),
    }
    submission.update((x, data[x]) for x in ('uid', 'log'))

    destination.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile(mode='w',
                            suffix='.json',
                            prefix='',
                            dir=destination,
                            delete=False) as fp:
        print(json.dumps(submission, indent=2), file=fp)

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
    event = Path(summary_data['log']).relative_to(dalgo_vars['logs'])
    log_data = dalgo_vars['logs'].joinpath(event)
    uid = uuid.uuid4()

    if fl.request.args:
        record(fl.request.args, dalgo_vars['output'])

    return fl.render_template(
        'base.html',
        uid=str(uid),
        name=event,
        summary=summary_file,
        log=pd.read_json(log_data).to_html(),
        responses=responses(summary_data),
    )

if __name__ == '__main__':
    app.run(host="0.0.0.0", debug=True)
