# Dalgo log summaries

Use an LLM to help with interpretation of Dalgo log messages

## Gist

Given a log from a Dalgo pipeline (Airbyte, dbt-run, dbt-test), and
whether the pipeline was successful or erroneous, ask an LLM summarize
what happened.

### Dalgo logs

This repo is meant to be run "offline" in the sense that logs are
located on disk. Further, logs are assumed to be organized as follows:

```
airbyte
│   ├── [org]
│   │   ├── [task]
│   │   │   └── [outcome].json
dbt
├── [org]
│   ├── [task]
│   │   ├── dbt-[action]
│   │   │   └── [outcome].json
```

where,

| Variable | Meaning |
|---|---|
| org | Organization that owned the pipeline |
| task | Pipeline's task ID |
| action | DBT action (deps, clean, test, run, docs-generate)
| outcome | Run status (success, failure)

### LLM prompt generation

System and user prompts are generated based on the log file path.
Going from path to prompt is handled by `src/log2prompt.py`.

#### System

The system prompt is a template (`prompts/system.txt`) that is filled
based on the pipeline. For DBT logs, the action is taken into
consideration. A JSON (`prompts/system.json`) is maintained for
mapping pipeline/action to specific context.

#### User

The user prompt is a static file whose name corresponds to the
outcome; see `prompts/user`. Lines in the user prompt file are meant
to be fed sequentially to the LLM, mimicking the interaction a user
might have:

```
line 1
[response]
line 2
[response]
...
line n
[response]
```

### LLM interaction

Interaction with the LLM happens through `src/log-chat.py`. Given the
prompts and the log file, the script creates an OpenAI assistant. The
log file is attached to the assistant using the "file search"
tool. Messages are created for each line in the user prompt. The file
search tool knows each message pertains to the log file.

Responses from the LLM are packaged into a JSON and sent to stdout.

## Assessment

The assessment tool is a web app (Flask) that allows users to rate the
LLM responses. It presents the log name, log contents, and each prompt
and response from the LLM. The user is provided radio buttons that
allow them to judge the answers.

Each judgment is written to disk as a JSON.
