#!/bin/bash

ROOT=`git rev-parse --show-toplevel`

export PYTHONPATH=$ROOT
export PYTHONLOGLEVEL=info

source $HOME/.keys/open-ai.rc || exit 1
source $ROOT/venv/bin/activate

logs=$HOME/etc/dalgo/logs
suffix=.json

for l in $logs/*; do
    case `basename $l` in
	airbyte) s_prompt=$ROOT/prompts/system/airbyte ;;
	prefect) s_prompt=$ROOT/prompts/system/dbt ;;
	*) continue ;;
    esac

    find $l -name "*$suffix" \
	| while read; do
	name=`realpath --relative-to=$logs $REPLY`
	for f in $ROOT/prompts/user-flows/*; do
	    o_path=$ROOT/summary/$name/`basename --suffix=.json $l`
	    o_name=`basename $f`.json.gz

	    mkdir --parents $o_path
	    python log-chat.py \
		   --log-file $REPLY \
		   --user-flow $f \
		   --system-prompt $s_prompt \
		| gzip --to-stdout > $o_path/$o_name
	done
    done
done
