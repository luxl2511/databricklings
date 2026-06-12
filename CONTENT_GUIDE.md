# Content authoring guide

How lessons and questions for databricklings are written. Content lives in `content/`,
app code never needs to change for new content.

## Files

- `content/domains.yaml`: the 10 exam domains with weights. Do not edit.
- `content/lessons/dNN-lMM-slug.yaml`: one file per lesson.
- `content/questions/dNN.yaml`: one file per domain holding all its questions.

## Lesson schema

```yaml
id: d06-l02            # dNN-lMM, NN = domain id, MM = order within domain
domain: 6
order: 2               # unlock order within the domain
title: OPTIMIZE, VACUUM and time travel
body: |
  Markdown study text, 300 to 600 words. Use ## headings (sentence case),
  fenced code blocks with language tags (```python, ```sql, ```yaml).
exercises:             # 3 to 6 per lesson
  - type: mcq          # mcq | multi | predict_output | spot_bug | fill_blank
    prompt: What does VACUUM remove?
    code: |            # optional snippet shown above the options
      VACUUM events RETAIN 0 HOURS
    code_lang: sql     # python | sql | yaml | text (default python)
    options:           # 2-5 options for choice types
      - data files no longer referenced by the table and older than the retention window
      - old table versions from the transaction log
    answer: [0]        # zero-based indices; multi answers like [0, 2]
    explanation: |
      Why the right answer is right and why each wrong option is wrong.
    verify: false      # true when a fact could not be confirmed in the docs
  - type: fill_blank
    prompt: Name the cloudFiles option that rescues unparseable columns.
    answers: ["_rescued_data", "rescued_data"]   # accepted typed answers, case-insensitive
    explanation: ...
sources:               # optional, urls used while writing (ignored by the app)
  - https://docs.databricks.com/...
```

## Question schema

```yaml
questions:
  - id: d06-q001       # dNN-qXXX, unique
    domain: 6
    subtopic: vacuum   # short kebab-case tag, reused across related questions
    difficulty: medium # easy | medium | hard
    type: multiple_choice   # or multi_select
    stem: |
      Scenario text. Realistic situation, then the actual question.
    code: |            # optional
      ...
    code_lang: sql
    options:
      - ...            # 4-5 options, all plausible
    answer: [2]
    explanation: |
      Covers the correct option and every distractor.
    verify: false
    sources:
      - https://docs.databricks.com/...
```

## Quality bar

- Scenario questions, not trivia. Describe a pipeline, an error, a cost problem or a
  security requirement, then ask for the best approach. Distractors are things that
  work but lose on cost, correctness or maintainability.
- Every explanation addresses all options, not only the correct one.
- Facts come from official docs (docs.databricks.com, learn.microsoft.com/azure/databricks,
  spark.apache.org). Anything not confirmed there gets `verify: true`.
- Nothing is copied from practice exam providers or braindumps. All original.
- Current product names: Lakeflow Jobs, Lakeflow Declarative Pipelines (mention the
  former DLT name once per domain where relevant), Unity Catalog, Databricks Asset
  Bundles, Auto Loader.

## Writing style

- Plain direct sentences. No em dashes, no emojis, no "robust/seamless/comprehensive/
  leverage" filler, no rule-of-three padding, sentence case headings.
- Code examples runnable and realistic, table and column names like a real lakehouse
  (orders, events, customers_silver).

## Validation

```
uv run python scripts/validate_content.py
```

Loads everything, enforces the schema, prints per-domain counts and verify-flagged ids.

## Target volume

| domain | weight | lessons | questions |
|--------|--------|---------|-----------|
| 1 develop | 22% | 11 | 55 |
| 2 ingest | 7% | 3 | 18 |
| 3 transform | 10% | 5 | 25 |
| 4 share | 5% | 3 | 13 |
| 5 monitor | 10% | 5 | 25 |
| 6 optimize | 13% | 7 | 33 |
| 7 secure | 10% | 5 | 25 |
| 8 govern | 7% | 4 | 18 |
| 9 deploy | 10% | 5 | 25 |
| 10 model | 6% | 3 | 15 |
| total | 100% | 51 | 252 |
