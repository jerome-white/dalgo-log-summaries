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

if __name__ == '__main__':
    arguments = ArgumentParser()
    arguments.add_argument('--model', default='gpt-4o')
    arguments.add_argument('--log-file', type=Path)
    arguments.add_argument('--user-prompt', type=Path)
    arguments.add_argument('--system-prompt', type=Path)
    args = arguments.parse_args()

    messenger = Messenger(args.model)

    prompts = (x.read_text() for x in (args.system_prompt, args.log_file))
    content = '\n\n'.join(prompts)
    messenger.push('system', content)

    with args.user_prompt.open() as fp:
        for (i, line) in enumerate(fp):
            logging.warning(i)
            messenger.push('user', line.strip())
            content = messenger.send()
            print('#' * 70, content, sep='\n', end='\n\n')
            messenger.push('assistant', content)
