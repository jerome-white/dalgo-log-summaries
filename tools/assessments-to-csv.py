import sys
import csv
import json
from pathlib import Path
from argparse import ArgumentParser
from dataclasses import dataclass, asdict, fields

from mylib import Logger

@dataclass
class Annotation:
    date: str
    log: str
    prompt: str
    judgement: str

if __name__ == '__main__':
    arguments = ArgumentParser()
    arguments.add_argument('--results', type=Path)
    args = arguments.parse_args()

    fieldnames = [ x.name for x in fields(Annotation) ]
    writer = csv.DictWriter(sys.stdout, fieldnames=fieldnames)
    writer.writeheader()

    submissions = set()
    for i in args.results.iterdir():
        data = json.loads(i.read_text())

        uid = data['uid']
        if uid in submissions:
            Logger.warning(uid)
            continue
        submissions.add(uid)

        (date, log) = map(data.get, ('date', 'log'))
        for a in data['annotations']:
            kwargs = { x: a[x] for x in ('prompt', 'judgement') }
            row = Annotation(date, log, **kwargs)
            writer.writerow(asdict(row))
