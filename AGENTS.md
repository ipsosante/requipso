## Requipso

Requipso builds query pipelines on ipso health data (the RED export). A study is described in a Google Sheet; the app produces an inclusion flowchart, a descriptive table, and patient lists.

Read the page that matches the change before editing. The docs are the source of truth; this file only points at them.

Documentation root: `requipso/docs/pages/`. Config and nav: `requipso/docs/mkdocs.yml`.

## Where to read

| Task | Page |
| --- | --- |
| What the product does, vocabulary | `requipso/docs/pages/index.md` |
| How a user fills the Sheet and runs the app | `requipso/docs/pages/guide/demarrage.md` and the other files in `guide/` |
| One block's behavior, parameters, and examples | `requipso/docs/pages/blocs/index.md`, then the block's page |
| Module map and request flow | `requipso/docs/pages/technique/architecture.md` |
| RED tables and the `Data` object | `requipso/docs/pages/technique/donnees.md` |
| Block class hierarchy and `transform` | `requipso/docs/pages/technique/blocs-internes.md` |
| Parameter models | `requipso/docs/pages/technique/parametres-internes.md` |
| Sheet tabs to Python objects | `requipso/docs/pages/technique/chargement-sheet.md` |
| Inclusion graph | `requipso/docs/pages/technique/pipeline.md` |
| Descriptive table | `requipso/docs/pages/technique/tableau-descriptif.md` |
| Free-text / NLP blocks | `requipso/docs/pages/technique/nlp.md` |
| Add a block | `requipso/docs/pages/technique/ajouter-un-bloc.md` |
| Refresh the Sheet catalog after a block change | `requipso/docs/pages/technique/export-signatures.md` |
| Setup, commands, docs build, release | `requipso/docs/pages/technique/developpement.md` |

The RED column schema is described in `donnees.md` (dbdocs.io). There is no `RED.dbml` in this repo.

## Conventions

- Python 3.12 only (`requires-python` in `pyproject.toml`). Use `uv sync`, then `uv run`.
- The Google Sheet is the user interface. Block parameters arrive as strings and are validated by Pydantic (`extra="forbid"`).
- A block is a class under `requipso/pipes/`. `build_block_registry` discovers it; do not register it by hand.
- Names of `transform` arguments are the RED table names to load. Follow `ajouter-un-bloc.md` for the return columns.
- Tables are Polars DataFrames.
- Block pages and the `🔒 Blocks` sheet are generated from `Field(description=…)` and `BlockConfig`. Do not hand-edit those tables. After a user-visible block change, run `uv run python scripts/signature_exporter.py`. Docs pick the change up on the next MkDocs build.
- Check docs with `uv run mkdocs build -f requipso/docs/mkdocs.yml --strict`.
- Lint and types: `uv run ruff check .`, `uv run ruff format .`, `uv run mypy requipso`.
- RED exports are personal health data. Do not copy them out of the environment, and do not commit them.
