# AGENTS.md — server/ (Django 5.2 + Ninja)

Managed with `uv` (POSIX era). On Windows use the checked-out venv `server/.venv-win` (`.\.venv-win\Scripts\python.exe -m pytest` 등 — WSL 제거됨, 2026-07-01). Project layout: `config/` (settings base/dev/test, api, celery), `apps/<domain>/` (24 narrow domain apps = 메이드era 19 + 신규 5: creator·social·content·commerce·membership).

## Rules (incident-based, CONSTRAINTS #25/#27/#38)

- Every function takes type hints; every public function/class has a docstring (*why*, not *what* — no restating the code).
- **Migrations: 정식 전환 완료(2026-07-09 · ASS-266 · #25 승인 하).** 모델 보유 전 앱이 실 마이그레이션(`0001_initial`)을 갖고, 테이블은 `migrate`로 생성된다(테스트 러너 포함). 전 앱이 초기 마이그레이션을 함께 갖추어 과거의 "한 앱만 0001 → unmigrated FK(`identity.Account`) 파손" 문제는 해소됐다. 모델 변경 시 `makemigrations`로 마이그레이션을 갱신하고 `makemigrations --check`는 항상 clean이어야 한다(모델↔마이그레이션 동기). **단, migrations 디렉토리 쓰기는 hook이 차단하므로 생성은 `ALLOW_MIGRATIONS=1` 인간승인 하에서만, `migrate`(로컬 초과)도 human-gated(#25).** django-linear-migrations로 선형 강제. 배포 스키마 provisioning은 `migrate`(NOT `--run-syncdb`).
- Never read or commit `.env` / credentials. Only `.env.example` is tracked.
- Ninja routers live in each domain app's `api.py` and attach to the single `config.api` instance. Keep view logic separable from schemas (DRF fallback path, ADR-0001).
- Keep app boundaries narrow; don't reach across domains via direct model imports once models exist.

## Verify (machine-checkable, run from server/)

- Lint: `uv run ruff check .`
- Types: `uv run mypy .`
- All tests: `uv run pytest`
- One test fast: `uv run pytest apps/<domain>/tests/test_smoke.py::<name>`
- Migrations committed: `uv run python manage.py makemigrations --check --dry-run --settings=config.settings.test`
