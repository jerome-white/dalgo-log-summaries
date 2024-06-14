#!/bin/bash

ROOT=`git rev-parse --show-toplevel`

export PYTHONPATH=$ROOT
export PYTHONLOGLEVEL=info

source $HOME/.keys/open-ai.rc || exit 1
source $ROOT/venv/bin/activate

_logs=$HOME/etc/dalgo/logs
_suffix=.json
_prompts=$ROOT/prompts
_output=$ROOT/summary

prompts=`mktemp --directory`
find $_logs -name "*${_suffix}" \
    | while read; do
    s_prompt=`mktemp --tmpdir=$prompts`
    lname=`realpath --relative-to=$_logs $REPLY`
    output=$_output/${lname}.gz
    if [ -e $output ]; then
	continue
    fi
    o_path=`dirname $output`
    python $ROOT/src/log2prompt.py \
	   --log $lname \
	   --substitutions $_prompts/system.json \
	   --system-prompt $_prompts/system.txt > $s_prompt \
	|| continue
    cat <<EOF
mkdir --parents $o_path && \
    python $ROOT/src/log-chat.py \
	   --log-file $REPLY \
	   --system-prompt $s_prompt \
	   --user-prompt $_prompts/user.txt \
	| gzip --to-stdout > $output
EOF
done | parallel --will-cite --line-buffer --delay 30 --retries 5
rm --recursive --force $prompts
