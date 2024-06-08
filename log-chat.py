import math
import time
import json
import functools as ft
from pathlib import Path
from argparse import ArgumentParser

from openai import OpenAI

from mylib import Logger

class AssistantMessage:
    def __init__(self, message):
        self.message = message

    def __iter__(self):
        for m in self.message:
            for c in m.content:
                yield c.text.value

    def __str__(self):
        return '\n\n'.join(self)

class FileAssistant:
    _tools = [{
        'type': 'file_search',
    }]

    @staticmethod
    def parse_wait_time(err):
        if err.code == 'rate_limit_exceeded':
            for i in err.message.split('. '):
                if i.startswith('Please try again in'):
                    (*_, seconds) = i.split()
                    assert seconds.endswith('s')
                    return float(seconds[:-1])

        raise TypeError(err.code)

    def __init__(self, log_file, instructions, model, retries):
        self.client = OpenAI()
        self.retries = retries

        with log_file.open('rb') as fp:
            self.document = self.client.files.create(
                file=fp,
                purpose='assistants',
            )
        self.assistant = self.client.beta.assistants.create(
            model=model,
            temperature=1e-6,
            tools=self._tools,
            instructions=instructions,
        )
        self.thread = self.client.beta.threads.create()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.client.files.delete(self.document.id)
        self.client.beta.threads.delete(self.thread.id)
        self.client.beta.assistants.delete(self.assistant.id)

    def query(self, content):
        message = self.client.beta.threads.messages.create(
            self.thread.id,
            role='user',
            content=content,
            attachments=[{
                'tools': self._tools,
                'file_id': self.document.id,
            }],
        )

        for i in range(self.retries):
            run = self.client.beta.threads.runs.create_and_poll(
                thread_id=self.thread.id,
                assistant_id=self.assistant.id,
            )
            if run.status == 'completed':
                break
            Logger.error('%s (%d): %s', run.status, i + 1, run.last_error)

            rest = math.ceil(self.parse_wait_time(run.last_error))
            Logger.warning('Sleeping %ds', rest)
            time.sleep(rest)

        messages = self.client.beta.threads.messages.list(
            thread_id=self.thread.id,
            run_id=run.id,
        )
        self.client.beta.threads.messages.delete(
            message_id=message.id,
            thread_id=self.thread.id,
        )

        return AssistantMessage(messages)

#
#
#
class ChatEncoder(json.JSONEncoder):
    @ft.singledispatchmethod
    def default(self, obj):
        return super().default(obj)

    @default.register
    def _(self, obj: Path):
        return str(obj)

    @default.register
    def _(self, obj: AssistantMessage):
        return str(obj)

#
#
#
def interact(flow):
    with flow.open() as fp:
        for line in fp:
            yield line.strip()

def chat(args):
    instructions = args.system_prompt.read_text()
    with FileAssistant(args.log_file,
                       instructions,
                       args.model,
                       args.retries) as fa:
        for (i, line) in enumerate(interact(args.user_prompt)):
            Logger.info('%s: %s', i, line)
            response = fa.query(line)
            yield {
                'prompt': line,
                'response': response,
            }

if __name__ == '__main__':
    arguments = ArgumentParser()
    arguments.add_argument('--model', default='gpt-4o')
    arguments.add_argument('--retries', default=5)
    arguments.add_argument('--log-file', type=Path)
    arguments.add_argument('--user-prompt', type=Path)
    arguments.add_argument('--system-prompt', type=Path)
    args = arguments.parse_args()

    Logger.info(args.log_file)
    result = {
        'log': args.log_file,
        'model': args.model,
        'instructions': args.system_prompt.read_text(),
        'dialogue': list(chat(args)),
    }

    print(json.dumps(result, indent=2, cls=ChatEncoder))
