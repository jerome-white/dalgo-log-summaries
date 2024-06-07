import sys
import json
from string import Template
from pathlib import Path
from argparse import ArgumentParser

from openai import OpenAI

from mylib import Logger

class Messenger:
    def __init__(self, model):
        self.model = model
        self.client = OpenAI()
        self.messages = []

    def push(self, role, content):
        self.messages.append({
            'role': role,
            'content': content,
        })

    def send(self):
        response = self.client.chat.completions.create(
            model=self.model,
            temperature=1e-6,
            messages=self.messages,
        )
        (message, ) = response.choices

        return message.message.content

def sysmsg(system, log):
    (s, l) = (x.read_text() for x in (system, log))
    message = Template(s)
    return message.substitute(log=l)

if __name__ == '__main__':
    arguments = ArgumentParser()
    arguments.add_argument('--model', default='gpt-4o')
    arguments.add_argument('--output', type=Path)
    arguments.add_argument('--log-file', type=Path)
    arguments.add_argument('--user-flow', type=Path)
    arguments.add_argument('--system-prompt', type=Path)
    args = arguments.parse_args()

    content = sysmsg(args.system_prompt, args.log_file)

    messenger = Messenger(args.model)
    messenger.push('system', content)

    with args.user_flow.open() as fp:
        for (i, line) in enumerate(fp):
            Logger.info(i)
            output = args.output.joinpath(f'{i:03}')

            messenger.push('user', line.strip())
            content = messenger.send()
            output.write_text(content)
            messenger.push('assistant', content)
