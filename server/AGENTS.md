# AGENTS.md — server/ (Django 5.2 + Ninja)

Managed with `uv`. Project layout: `config/` (settings base/dev/test, api, celery), `apps/<domain>/` (17 narrow domain apps).

## Rules (incident-based, CONSTRAINTS #25/#27/#38)

- Every function takes type hints; every public function/class has a docstring (*why*, not *what* — no restating the code).
- Migrations: `makemigrations` only. Never edit migration files and never `migrate` beyond local — that is human-gated. django-linear-migrations enforces linearity.
- Never read or commit `.env` / credentials. Only `.env.example` is tracked.
- Ninja routers live in each domain app's `api.py` and attach to the single `config.api` instance. Keep view logic separable from schemas (DRF fallback path, ADR-0001).
- Keep app boundaries narrow; don't reach across domains via direct model imports once models exist.

## Verify (machine-checkable, run from server/)

- Lint: `uv run ruff check .`
- Types: `uv run mypy .`
- All tests: `uv run pytest`
- One test fast: `uv run pytest apps/<domain>/tests/test_smoke.py::<name>`
- Migrations committed: `uv run python manage.py makemigrations --check --dry-run --settings=config.settings.test`
