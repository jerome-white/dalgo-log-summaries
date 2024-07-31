import sys
import math
import time
import json
import itertools as it
from pathlib import Path
from argparse import ArgumentParser
from dataclasses import dataclass, asdict

import pandas as pd
from openai import OpenAI

from mylib import Logger

class CitationManager:
    def __init__(self, annotations, client, start=1):
        self.body = {}
        self.citations = []

        for (i, a) in enumerate(annotations, start):
            reference = f'[{i}]'
            self.body[a.text] = reference

            document = client.files.retrieve(a.file_citation.file_id)
            citation = '{} {}:{}--{}'.format(
                reference,
                document.filename,
                a.start_index,
                a.end_index,
            )
            self.citations.append(citation)

    def __len__(self):
        return len(self.citations)

    def __str__(self):
        raise NotImplementedError()

    def __iter__(self):
        raise NotImplementedError()

    def replace(self, body):
        for i in self:
            body = body.replace(*i)

        return body

class NumericCitations(CitationManager):
    def __str__(self):
        return '\n\n{}'.format('\n'.join(self.citations))

    def __iter__(self):
        for (k, v) in self.body.items():
            yield (k, f' {v}')

class NoCitations(CitationManager):
    def __str__(self):
        return ''

    def __iter__(self):
        yield from zip(self.body, it.repeat(''))

#
#
#
class AssistantMessage:
    def __init__(self, client, citation):
        self.client = client
        self.citation = citation

    def __call__(self, message):
        refn = 1
        for m in message:
            for c in m.content:
                cite = self.citation(c.text.annotations, self.client, refn)
                body = cite.replace(c.text.value)

                yield f'{body}{cite}'

                refn = len(cite) + 1

    def to_string(self, message):
        return '\n'.join(self(message))

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

    def __init__(
            self,
            client,
            parser,
            log_file,
            instructions,
            model,
            retries,
    ):
        self.client = client
        self.parser = parser
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

        return self.parser.to_string(messages)

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
    client = OpenAI()
    citations = NumericCitations if args.with_citations else NoCitations
    parser = AssistantMessage(client, citations)

    with FileAssistant(client,
                       parser,
                       args.log_file,
                       str(instruction),
                       args.model,
                       args.retries) as fa:
        for (i, prompt) in enumerate(instruction):
            Logger.info('%s: %s', i, prompt)
            response = fa.query(prompt)
            yield ChatResponse(prompt, response)

if __name__ == '__main__':
    arguments = ArgumentParser()
    arguments.add_argument('--model', default='gpt-4o')
    arguments.add_argument('--retries', default=5)
    arguments.add_argument('--log-file', type=Path)
    arguments.add_argument('--with-citations', action='store_true')
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
