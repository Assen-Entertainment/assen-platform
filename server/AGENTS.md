# AGENTS.md — server/ (Django 5.2 + Ninja)

Managed with `uv` (POSIX era). On Windows use the checked-out venv `server/.venv-win` (`.\.venv-win\Scripts\python.exe -m pytest` 등 — WSL 제거됨, 2026-07-01). Project layout: `config/` (settings base/dev/test, api, celery), `apps/<domain>/` (24 narrow domain apps = 메이드era 19 + 신규 5: creator·social·content·commerce·membership).

## Rules (incident-based, CONSTRAINTS #25/#27/#38)

- Every function takes type hints; every public function/class has a docstring (*why*, not *what* — no restating the code).
- **Migrations: 만들지 마라.** 전 앱이 migration-less(모델만)이며 테이블은 `migrate --run-syncdb`로 생성된다(테스트 러너 포함). 새 모델에 `makemigrations`를 실행하면 그 앱만 0001이 생겨 unmigrated FK(`identity.Account` 등)에 의존해 깨진다 — 생성됐다면 삭제. `makemigrations --check`는 항상 clean이어야 한다. 정식 마이그레이션 전환·`migrate`(로컬 초과)는 human-gated(#25). django-linear-migrations는 그 전환 시점을 위해 유지.
- Never read or commit `.env` / credentials. Only `.env.example` is tracked.
- Ninja routers live in each domain app's `api.py` and attach to the single `config.api` instance. Keep view logic separable from schemas (DRF fallback path, ADR-0001).
- Keep app boundaries narrow; don't reach across domains via direct model imports once models exist.

## Verify (machine-checkable, run from server/)

- Lint: `uv run ruff check .`
- Types: `uv run mypy .`
- All tests: `uv run pytest`
- One test fast: `uv run pytest apps/<domain>/tests/test_smoke.py::<name>`
- Migrations committed: `uv run python manage.py makemigrations --check --dry-run --settings=config.settings.test`
