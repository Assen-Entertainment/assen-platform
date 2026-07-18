# 신규 개발자 온보딩 — Day 1

순수 Windows 툴체인(`docs/adr/0006-toolchain-windows-uv.md`, WSL 없음)에서 4개 스택
(server → web → Flutter → e2e)을 순서대로 셋업한다. 각 절은 검증 명령까지 포함한다 —
빌드/테스트가 green이어야 다음 절로 넘어간다.

## 0. 사전 준비

| 항목 | 비고 |
|---|---|
| Git (Windows) | origin은 HTTPS, GitHub `Assen-Entertainment/assen-platform`(private) |
| Python 3.12 | `server/pyproject.toml`의 `requires-python = ">=3.12,<3.13"`. `server/.venv-win`은 이미 체크아웃돼 있으므로 시스템 Python은 `uv`가 venv를 재생성할 때만 필요 |
| [uv](https://docs.astral.sh/uv/) | 의존성 관리자. Windows에서는 **venv 생성/동기화**에만 쓰고, 실행은 `.venv-win`을 직접 호출한다(아래 §2) |
| Node 24 / npm 11 | `web/`·`landing/`·`e2e/` 공통. pnpm 불요 |
| [Flutter SDK(Windows 네이티브)](https://docs.flutter.dev/get-started/install/windows) | `apps/assen_mobile` + `packages/*`. 이 리포는 `C:\Users\daisy\flutter`에 설치돼 있다(팀 표준 경로) |
| Docker Desktop | server의 로컬 Postgres 16 / Redis 7(수동 기동, `docker-compose.yml`) |

클론 후 1회:

```powershell
sh scripts/install-hooks.sh   # git pre-commit hook 활성화(core.hooksPath=scripts/hooks)
```

작업 전 `AGENTS.md`(루트, 검증 계약·GitOps·금지 영역)와 `docs/CONSTRAINTS.md`를 읽는다.

## 1. server (Django + Ninja)

```powershell
cd server
Copy-Item .env.example .env   # 로컬 값으로 편집(DATABASE_URL 등). .env는 git-ignored

# venv 동기화 — UV_PROJECT_ENVIRONMENT로 타깃을 .venv-win에 고정한다.
$env:UV_PROJECT_ENVIRONMENT = ".venv-win"
uv sync

# Postgres/Redis (Docker Desktop이 떠 있어야 함)
docker compose -f ..\docker-compose.yml up -d postgres redis

# 스키마 적용 (2026-07-09 마이그레이션 정식 전환 — 각 앱이 0001_initial 보유)
.\.venv-win\Scripts\python.exe manage.py migrate

# 검증
.\.venv-win\Scripts\python.exe -m ruff check .
.\.venv-win\Scripts\python.exe -m mypy .
.\.venv-win\Scripts\python.exe -m pytest
.\.venv-win\Scripts\python.exe manage.py makemigrations --check --dry-run --settings=config.settings.test

# 개발 서버
.\.venv-win\Scripts\python.exe manage.py runserver 127.0.0.1:8000
```

패키지를 상시 추가할 때는 `pyproject.toml`을 손으로 고치고 `uv sync`를 다시 돌리거나,
바로 설치만 하려면:

```powershell
uv pip install --python .venv-win/Scripts/python.exe <package>
```

규칙 상세(마이그레이션 게이트, 도메인 앱 경계 등)는 `server/AGENTS.md` 참조.

## 2. web (React + Next.js)

```powershell
cd web
Copy-Item .env.example .env.local   # 미설정이어도 mock 폴백으로 동작(B5)
npm install --legacy-peer-deps      # react 19 peer 경고 회피

npm run build   # 타입체크 + ESLint 게이트 + SSG
npm test        # Vitest
npm run dev     # http://localhost:3000 (/gallery 에서 DS 42종 확인)
```

상세는 `web/ASSEN_WEB_SETUP.md`. 시각 회귀 게이트는 `web/ASSEN_DS_VISUAL_GATE.md`.

## 3. Flutter (모바일)

```powershell
dart pub get
dart run melos run format
dart run melos run analyze
dart run melos run test
```

개별 파일만: `flutter test packages/<pkg>/test/<file>_test.dart`. 규칙(Riverpod 3.x 전용,
`ui_kit` 경유 스타일링, golden 파일 인간 게이트 등)은 `apps/AGENTS.md` 참조.

## 4. e2e (Playwright, 선택)

서버를 라이브로 띄운 상태에서 도는 API 레벨 QA 게이트 — CI에는 안 붙어 있고 머지 전 수동/에이전트
실행이다. 절차는 `e2e/README.md`(PowerShell, 시드 스크립트 포함)를 그대로 따른다.

## 트러블슈팅

- **`uv sync` 실패 — 파일 잠금**: 실행 중인 로컬 서버(`runserver`)가 `.venv-win`의 `.pyd`
  (컴파일된 확장 모듈)를 점유하고 있으면 `uv sync`가 실패한다. 서버 프로세스를 정지한 뒤
  재시도한다.
- **`uv sync`가 엉뚱한 곳에 venv를 만든다**: `UV_PROJECT_ENVIRONMENT=.venv-win`을 세션에
  설정했는지 확인한다 — 없으면 uv가 기본 위치(`.venv`)에 새로 만든다.
- **패키지 하나만 급하게 추가**: `pyproject.toml`을 갱신하기 전에 먼저 써보려면
  `uv pip install --python .venv-win/Scripts/python.exe <package>` (§1 참조). 검증 통과 후
  `pyproject.toml`에도 반영해 `uv sync`로 재동기화한다.
- **`manage.py migrate`가 실패하거나 스키마가 안 맞는다**: 모델 변경 후 마이그레이션 파일이
  없으면 `makemigrations --check`가 dirty로 나온다. migrations 디렉토리 쓰기는 hook이
  차단하므로 생성은 `ALLOW_MIGRATIONS=1` 인간 승인 하에서만 한다(`server/AGENTS.md`).
- **`npm install`이 이상하게 실패한다(네이티브 바이너리 오류 등)**: `node_modules`가
  2026-07-01 이전 WSL 체크아웃에서 온 것이면 Windows 바이너리와 맞지 않는다 —
  `node_modules`를 지우고 Windows에서 `npm install`을 다시 돈다.
- **PowerShell에서 `manage.py shell < script.py`가 파싱 에러를 낸다**: PowerShell은 외부
  명령에 대한 `<` stdin 리다이렉트를 지원하지 않는다. 대신
  `manage.py shell -c "exec(open('script.py', encoding='utf-8').read())"` 패턴을 쓴다
  (`e2e/README.md`가 이 패턴으로 작성돼 있다).
- **Docker Desktop이 안 떠 있다**: server의 Postgres/Redis는 로컬에 상주 서비스가 아니라
  Docker Desktop을 수동 기동해야 뜬다 — `docs/deployment.md` "Local / Dev Build" 참조.
