import json
from string import Template
from pathlib import Path
from argparse import ArgumentParser

from mylib import Logger

if __name__ == '__main__':
    arguments = ArgumentParser()
    arguments.add_argument('--log', type=Path)
    arguments.add_argument('--substitutions', type=Path)
    arguments.add_argument('--system-prompt', type=Path)
    args = arguments.parse_args()

    prompt = Template(args.system_prompt.read_text())
    pipeline = json.loads(args.substitutions.read_text())
    (task, *_, subtask) = args.log.parts

    if task not in pipeline:
        name = Path(subtask)
        if name.stem not in pipeline:
            Logger.error(args.log)
            raise LookupError(args.log)
        task = name.stem

    print(prompt.substitute(pipeline=pipeline[task]))
