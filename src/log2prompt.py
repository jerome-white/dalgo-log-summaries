import sys
import json
import functools as ft
from string import Template
from pathlib import Path
from argparse import ArgumentParser

# from mylib import Logger

def head(path):
    assert not path.is_absolute()
    (h, *_) = path.parts
    return h

class LogNameParser:
    def __init__(self, log):
        self.log = log

    def __bool__(self):
        return self.log.stem == 'success'

    @property
    def ltype(self):
        raise NotImplementedError()

    @classmethod
    def from_path(cls, path):
        root = head(path)
        if root == 'airbyte':
            parser = AirbyteNameParser
        elif root == 'dbt':
            parser = PrefectNameParser
        else:
            raise LookupError(path)

        return parser(path)

class AirbyteNameParser(LogNameParser):
    @property
    def	ltype(self):
        return head(self.log)

class PrefectNameParser(LogNameParser):
    @property
    def	ltype(self):
        return self.log.parent.name

#
#
#
class ResultEncoder(json.JSONEncoder):
    @ft.singledispatchmethod
    def default(self, obj):
        return super().default(obj)

    @default.register
    def _(self, obj: Path):
        return str(obj)

#
#
#
if __name__ == '__main__':
    arguments = ArgumentParser()
    arguments.add_argument('--log', type=Path)
    arguments.add_argument('--substitutions', type=Path)
    arguments.add_argument('--system-prompt', type=Path)
    arguments.add_argument('--user-prompts', type=Path)
    args = arguments.parse_args()

    parser = LogNameParser.from_path(args.log)

    # System prompt
    s_subs = json.loads(args.substitutions.read_text())
    pipeline = s_subs[parser.ltype]

    p_template = Template(args.system_prompt.read_text().strip())
    system = p_template.substitute(pipeline=pipeline)

    # User prompt
    name = 'success' if parser else 'failure'
    user = (args
            .user_prompts
            .joinpath(name)
            .with_suffix('.txt')
            .read_text()
            .strip()
            .split('\n'))

    # Report
    prompt = {
        'system': system,
        'user': user,
    }
    json.dump(prompt, sys.stdout, indent=2, cls=ResultEncoder)
