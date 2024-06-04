#!/bin/bash

ROOT=`git rev-parse --show-toplevel`

export PYTHONPATH=$ROOT
export PYTHONLOGLEVEL=info

source $HOME/.keys/open-ai.rc || exit 1
source $ROOT/venv/bin/activate

logs=$HOME/etc/dalgo/logs
suffix=.json

find $logs -name "*$suffix" \
    | while read; do
    out=$ROOT/summary/`realpath --relative-to=$logs $REPLY`

    o_path=`dirname $out`
    o_name=`basename --suffix=$suffix $out`

    mkdir --parents $o_path
    python log-iterator.py \
	   --log-file $REPLY \
	   --user-prompt $ROOT/prompts/user-flow.txt \
	   --system-prompt $ROOT/prompts/system-enhanced.txt > $o_path/$o_name
done
