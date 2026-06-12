# databricklings

A terminal study app for the Databricks Certified Data Engineer Professional exam
(November 2025 syllabus). Guided lessons with checkpoint exercises in the spirit of
rustlings, plus a full exam simulator, spaced repetition and a stats dashboard.
Vim keybindings throughout, built with Textual.

Unofficial community project. Not affiliated with, endorsed by, or sponsored by
Databricks, Inc. Databricks is a trademark of Databricks, Inc. and is used here only
to refer to the platform the exam covers. All lessons and questions are original
material written against publicly available documentation.

## Install

Requires Python 3.12+ and [uv](https://docs.astral.sh/uv/).

```
git clone https://github.com/luxl2511/databricklings.git
cd databricklings
uv sync
uv run databricklings
```

## What's inside

- Learning path: 51 lessons across the 10 exam domains, lesson counts mirror the
  official domain weights. Each lesson is a short study text with code examples and
  3 to 6 checkpoint exercises. A lesson unlocks once the previous one is done,
  wrong checkpoints repeat until you pass them.
- Exam simulator: 59 questions, 120 minute countdown, questions sampled per the
  official domain weights, mark-for-review and free navigation, grading and
  per-domain breakdown at the end, full answer review with explanations.
- Quick drill: 10 or 20 questions, all domains, one domain, or your weak areas.
- Review due: every wrong answer enters a 5-box Leitner queue (0/1/3/7/14 day
  intervals). The queue surfaces what is due today.
- Stats: all-time accuracy per domain, lessons completed, exams taken, weakest
  subtopics.

The exam covers 10 domains: code development with Python/SQL (22%), ingestion (7%),
transformation and quality (10%), sharing and federation (5%), monitoring (10%),
cost and performance (13%), security (10%), governance (7%), debugging and
deploying (10%), data modelling (6%).

## Keybindings

Movement, everywhere:

| key | action |
|-----|--------|
| `j` / `k` | down / up |
| `h` / `l` | collapse / expand tree node |
| `gg` / `G` | top / bottom |
| `ctrl-d` / `ctrl-u` | half page down / up |
| `Esc` | back / close |
| `?` | keybinding cheatsheet |

Answering questions:

| key | action |
|-----|--------|
| `1`-`5` or `a`-`e` | pick an option |
| `space` | toggle option (multi select), mark for review (exam) |
| `Enter` | submit / confirm / next |
| `n` / `p` | next / previous question (exam) |
| `m` | mark for review (exam) |
| `f` | finish exam early |

Navigation screens:

| key | action |
|-----|--------|
| `space` | leader menu (which-key style): `e` exam, `l` lessons, `d` drill, `r` review, `s` stats, `q` quit |
| `l` `e` `d` `r` `s` | direct jump from the dashboard |
| `/` | fuzzy search lessons (type to filter, `ctrl-j`/`ctrl-k` move, Enter open) |
| `q` | quit (dashboard) |

## Progress

Stored in `~/.databricklings/progress.json`. Delete the file to start over.

## Adding your own questions

Content lives in `content/` as plain YAML, the app code never needs to change:

- `content/lessons/dNN-lMM-slug.yaml`: one file per lesson
- `content/questions/dNN.yaml`: one file per domain

See [CONTENT_GUIDE.md](CONTENT_GUIDE.md) for the schema. Validate with:

```
uv run python scripts/validate_content.py
```

Some items carry `verify: true`: the fact was written from documentation research but
could not be fully confirmed. Double-check those against the official docs before
relying on them.

## Development

```
uv run pytest
```

Tests cover progress tracking, Leitner scheduling, weighted sampling, scoring,
content validation and headless TUI flows (Textual Pilot).

## License

MIT, see [LICENSE](LICENSE).
