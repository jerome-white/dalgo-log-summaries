#!/bin/bash

ROOT=`git rev-parse --show-toplevel`

export PYTHONPATH=$ROOT
export PYTHONLOGLEVEL=info

source $HOME/.keys/open-ai.rc || exit 1
source $ROOT/venv/bin/activate

logs=$HOME/etc/dalgo/logs
suffix=.json

for l in $logs/*; do
    prompts=$ROOT/prompts/`basename $l`
    find $l -name "*$suffix" \
	| while read; do
	output=$ROOT/summary/`realpath --relative-to=$logs $REPLY`
	o_path=`dirname $output`
	cat <<EOF
mkdir --parents $o_path && \
    python $ROOT/log-chat.py \
	   --log-file $REPLY \
	   --system-prompt $prompts/system \
	   --user-prompt $prompts/user \
	| gzip --to-stdout > ${output}.gz
EOF
    done
done | parallel --will-cite --line-buffer --delay 30 --retries 5
