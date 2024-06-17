import sys
import math
import time
import json
from pathlib import Path
from argparse import ArgumentParser
from dataclasses import dataclass, asdict

import pandas as pd
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

    def to_string(self):
        return str(self)

class FileAssistant:
    _tools = [{
        'type': 'file_search',
    }]

    @staticmethod
    def parse_wait_time(err):
        if err.code == 'rate_limit_exceeded':
            for i in err.message.split('. '):
                if i.startswith('Please try again in'):
                    (*_, wait) = i.split()
                    return (pd
                            .to_timedelta(wait)
                            .total_seconds())

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
        else:
            raise TimeoutError('Message retries exceeded')

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
@dataclass
class Instruction:
    system: str
    user: list

    def __str__(self):
        return self.system

    def __iter__(self):
        yield from self.user

@dataclass
class ChatResponse:
    prompt: str
    response: str

def chat(instruction, args):
    with FileAssistant(args.log_file,
                       str(instruction),
                       args.model,
                       args.retries) as fa:
        for (i, prompt) in enumerate(instruction):
            Logger.info('%s: %s', i, prompt)
            response = (fa
                        .query(prompt)
                        .to_string())
            yield ChatResponse(prompt, response)

if __name__ == '__main__':
    arguments = ArgumentParser()
    arguments.add_argument('--model', default='gpt-4o')
    arguments.add_argument('--retries', default=5)
    arguments.add_argument('--log-file', type=Path)
    args = arguments.parse_args()

    Logger.info(args.log_file)

    kwargs = json.load(sys.stdin)
    instruction = Instruction(**kwargs)

    dialogue = chat(instruction, args)
    result = {
        'log': str(args.log_file),
        'model': args.model,
        'instructions': str(instruction),
        'dialogue': list(map(asdict, dialogue)),
    }

    print(json.dumps(result, indent=2))
