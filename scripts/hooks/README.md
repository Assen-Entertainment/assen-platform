# Assen Platform — Harness Hooks

Claude Code PreToolUse hook + git pre-commit hook으로 비가역 영역을 기계 강제 차단한다.
"자연어 지시는 보안 경계가 아니다" (CONSTRAINTS #25~#32).

---

## 계층 적용 범위 매트릭스 (ASS-133)

세션 형태에 따라 각 계층이 실제로 작동하는지 여부를 정리한다.

| 세션 형태 | guard.py (Claude Code PreToolUse) | git pre-commit | CI 최종 게이트 |
|-----------|-----------------------------------|----------------|----------------|
| assen-platform을 프로젝트 루트로 직접 연 Claude Code 세션 | **유효** — `.claude/settings.json` 로드됨 | **유효** — core.hooksPath=scripts/hooks 설정 시 | **유효** — 항상 |
| 부모 디렉터리(예: Assen/)를 루트로 연 세션 및 그 서브에이전트 | **inert** — settings.json 로드 안 됨, `${CLAUDE_PROJECT_DIR}` 불일치 | **유효** — worktree는 공유 core.hooksPath 상속, install-hooks.sh 1회 실행 시 | **유효** — 항상 |
| 에이전트 worktree (`.claude/worktrees/`) | **inert** — 위와 동일 | **유효** — git worktree는 core.hooksPath 공유 | **유효** — 항상 |
| IDE 플러그인 / 직접 git 조작 | 해당 없음 | **유효** — core.hooksPath 설정 시 | **유효** — 항상 |

### 한계로 남은 것

- **guard.py는 "assen-platform 직접 세션"에서만 유효하다.** `${CLAUDE_PROJECT_DIR}` 절대경로 폴백을 시도해도, 부모 디렉터리 세션에서는 settings.json 자체가 로드되지 않으므로 구조적으로 불가. 해결책: git pre-commit이 유일한 worktree/에이전트 방어 계층.
- **git pre-commit은 `install-hooks.sh` 1회 실행이 전제**다. 미실행 시 hook 미작동. CI에서 install+검증 스텝을 추가해 부트스트랩 누락을 잡는다 (ASS-133).
- **pre-commit 우회**: `git commit --no-verify`로 인간/에이전트가 강제 우회 가능. CI가 최종 게이트.
- **셸 변수·글로브 인자** (`rm "$FILE"`, `rm *_test.dart`)는 정적 분석 불가 — guard.py Failure Modes와 동일 한계.

---

## 구성 파일

| 파일 | 역할 |
|------|------|
| `guard.py` | Claude Code PreToolUse hook — 도구 호출 차단 |
| `pre-commit` | git pre-commit hook — 커밋 레벨 심층 방어 |
| `install-hooks.sh` | git core.hooksPath 설정 설치 스크립트 |
| `test_hooks.py` | guard.py 동작 검증 테스트 (python3 실행) |
| `test_pre_commit.sh` | pre-commit 행위 검증 테스트 (bash, 샌드박스 git repo) |

---

## 설치 (클론 후 1회 필수)

```sh
# git pre-commit hook 설치 — 클론 직후 반드시 1회 실행
sh scripts/install-hooks.sh
```

Claude Code hook(guard.py)은 `.claude/settings.json`에 이미 등록되어 있으므로
**assen-platform을 프로젝트 루트로 직접 연 세션**에서는 자동 활성화된다.
부모 디렉터리 세션·에이전트 worktree에서는 git pre-commit이 유일 방어 계층이므로
install-hooks.sh 실행이 더욱 중요하다.

---

## 차단 가드 상세

### `pre-commit` — git hook (심층 방어, ASS-133 확장)

| 가드 | 대상 | CONSTRAINTS | 오버라이드 |
|------|------|-------------|------------|
| 기존 테스트 파일 수정(M)/삭제(D) | `test_*.py`, `*_test.py`, `*_test.dart` (basename) | #31 | `ALLOW_TEST_EDIT=1` |
| 마이그레이션 staged | `**/migrations/*.py` | #25 | `ALLOW_MIGRATIONS=1` |
| 골든 파일 staged | `**/goldens/**`, `*.golden.*` | #31 | `ALLOW_GOLDEN=1` |
| .env 시크릿 staged | `.env`, `.env.*` (example/sample/template 제외) | #27 | 없음 — 절대 커밋 금지 |
| 생성 파일 staged | `*.g.dart`, `*.freezed.dart` | #32 | `ALLOW_GENERATED=1` |
| gitleaks 시크릿 스캔 | staged 전체 | #27 | 없음 (CI 최종 게이트) |

**신규 테스트 파일 추가(A)는 항상 허용.**

### `guard.py` — Claude Code PreToolUse

| 가드 | 대상 패턴 | CONSTRAINTS | 오버라이드 |
|------|-----------|-------------|------------|
| 마이그레이션 생성·수정 | `server/**/migrations/**/*.py` | #25 | 없음 (인간만) |
| 생성 파일 손편집 | `*.g.dart`, `*.freezed.dart` | #32 | 없음 |
| 골든 베이스라인 수정 | `**/goldens/**`, `*.golden.*` | #31 | 없음 |
| 시크릿 접근 | `.env`, `.env.*` | #27 | 없음 (`.env.example`/`.env.sample`/`.env.template`은 허용) |
| 기존 테스트 파일 수정 | `test_*.py`, `*_test.py`, `*_test.dart` | #31 | `ALLOW_TEST_EDIT=1` |
| 테스트 파일 삭제 (`rm`/`git rm`) | basename이 위 패턴 | #31 | `ALLOW_TEST_EDIT=1` |
| `--update-goldens` Bash | 명령에 포함 시 | #31 | 없음 |
| `manage.py migrate` / `django-admin migrate` | 토큰 기반 | #25 | `--check`, `--dry-run`은 허용 |
| `git push origin main` | ref 타깃 기반 (best-effort) | GitOps | 없음 |
| `rm -rf` | 경로 무관 | #28 | 없음 |
| `git push --force` / `-f` / `--force-with-lease` | | #28 | 없음 |
| `DROP TABLE` / `TRUNCATE` | SQL, 대소문자 무시 | #28 | 없음 |
| `manage.py flush` | | #28 | 없음 |

**신규 테스트 파일 생성(Write + 미존재 경로)은 항상 허용.**
**conftest.py, factories.py 등 헬퍼 모듈은 basename 기반으로 차단하지 않음.**

---

## 오버라이드 환경변수 (인간 전용)

오버라이드는 팀 리드/인간이 직접 검토 후에만 사용한다.

```sh
# 기존 테스트 수정이 불가피할 때 (guard.py + pre-commit)
ALLOW_TEST_EDIT=1 git commit -m "..."
ALLOW_TEST_EDIT=1 claude ...

# 마이그레이션 커밋이 불가피할 때 (pre-commit)
ALLOW_MIGRATIONS=1 git commit -m "..."

# 골든 파일 갱신 시 (pre-commit)
ALLOW_GOLDEN=1 git commit -m "..."

# 생성 파일 커밋이 불가피할 때 (pre-commit)
ALLOW_GENERATED=1 git commit -m "..."
```

---

## 동작 검증

```sh
# guard.py 55케이스 검증
python3 scripts/hooks/test_hooks.py

# pre-commit 15케이스 행위 검증 (샌드박스 git repo)
bash scripts/hooks/test_pre_commit.sh
```

---

## Failure Modes

| 상황 | 동작 | 이유 |
|------|------|------|
| JSON 파싱 실패 | fail-open (exit 0) | 가용성 트레이드오프 — Claude Code는 well-formed JSON을 보장하므로 정상 운영에서는 발생하지 않음 |
| guard.py 스크립트 미존재 | Claude Code가 hook 실패로 처리 | settings.json 절대경로(`${CLAUDE_PROJECT_DIR}`) 사용으로 CWD 우회 방지 |
| install-hooks.sh 미실행 | pre-commit inert | CI에서 install+검증 스텝으로 누락 감지 (ASS-133) |
| `git commit --no-verify` | pre-commit 우회됨 | CI가 최종 게이트 — 로컬 hook은 best-effort |
| gitleaks 미설치 | 경고만 출력, 커밋 허용 | CI gitleaks가 최종 게이트 |
| 부모 디렉터리 세션 / 에이전트 worktree | guard.py inert | 구조적 한계 — pre-commit + CI로 보완 (계층 매트릭스 참조) |
| `echo "DROP TABLE"` 등 문자열 내 SQL 키워드 | fail-safe 과차단(block) | 명령 실행과 문자열을 구별하지 않는다. 파괴적 명령 누락보다 드문 과차단이 안전 |
| `rm "$FILE"` / `rm *_test.dart` 셸 변수·글로브 인자 | 미감지(under-block) | 정적 토큰 분석의 구조적 한계 |

---

## 근거 (CONSTRAINTS 발췌)

- **#25**: migrations는 makemigrations 명령으로만 생성. 적용은 인간이 검토·승인.
- **#27**: AI는 .env 시크릿에 접근하지 않는다. .env.example로 스키마만 공유.
- **#28**: 파괴적 명령(rm -rf, force push, DROP/TRUNCATE, flush)은 인간 전용. 오버라이드 없음.
- **#31**: 골든 베이스라인·기존 테스트는 인간 승인 없이 변경 불가.
- **#32**: *.g.dart / *.freezed.dart는 build_runner 전용. 손편집 시 build_runner가 덮어씀.
- **GitOps**: main=prod 게이트. dev→main 릴리즈 PR로만 머지.
  브랜치 가드는 best-effort — 권위 게이트는 GitHub 브랜치 보호(현재 무료 플랜이라 미적용 — Pro 시 적용 권장).
