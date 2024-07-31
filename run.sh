#!/bin/bash

ROOT=`git rev-parse --show-toplevel`
VERSION=v3
SANDBOX=$ROOT/var/$VERSION

export PYTHONPATH=$ROOT
export PYTHONLOGLEVEL=info

source $HOME/.keys/open-ai.rc || exit 1
source $ROOT/venv/bin/activate

_logs=$HOME/etc/dalgo/logs-v2
# _name="*.json"
_name=failure.json
_prompts=$ROOT/prompts
_output=$SANDBOX/summary

find $_logs -name "$_name" \
    | while read; do
    lname=`realpath --relative-to=$_logs $REPLY`

    output=$_output/${lname}.gz
    if [ -e $output ]; then
	continue
    fi
    cat <<EOF
mkdir --parents `dirname $output` && \
    python $ROOT/src/log2prompt.py \
	   --log $lname \
	   --substitutions $_prompts/system.json \
	   --system-prompt $_prompts/system.txt \
	   --user-prompts $_prompts/user \
	| python $ROOT/src/log-chat.py --log-file $REPLY \
	| gzip --to-stdout > $output
EOF
done | parallel --will-cite --line-buffer --delay 30 --retries 5
