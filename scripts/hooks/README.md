# Assen Platform — Harness Hooks

Claude Code PreToolUse hook + git pre-commit hook으로 비가역 영역을 기계 강제 차단한다.
"자연어 지시는 보안 경계가 아니다" (CONSTRAINTS #25~#32).

---

## 구성 파일

| 파일 | 역할 |
|------|------|
| `guard.py` | Claude Code PreToolUse hook — 도구 호출 차단 |
| `pre-commit` | git pre-commit hook — 커밋 레벨 심층 방어 |
| `install-hooks.sh` | git core.hooksPath 설정 설치 스크립트 |
| `test_hooks.py` | 동작 검증 테스트 (python3 실행) |

---

## 설치

```sh
# 1. Claude Code hook — .claude/settings.json에 이미 등록됨 (자동)

# 2. git pre-commit hook 설치
sh scripts/install-hooks.sh
```

---

## 차단 가드 상세

### `guard.py` — Claude Code PreToolUse

| 가드 | 대상 패턴 | CONSTRAINTS | 오버라이드 |
|------|-----------|-------------|------------|
| 마이그레이션 생성·수정 | `server/**/migrations/**/*.py` | #25 | 없음 (인간만) |
| 생성 파일 손편집 | `*.g.dart`, `*.freezed.dart` | #32 | 없음 |
| 골든 베이스라인 수정 | `**/goldens/**`, `*.golden.*` | #31 | 없음 |
| 시크릿 접근 | `.env`, `.env.*` | #27 | 없음 (`.env.example`/`.env.sample`/`.env.template`은 허용) |
| 기존 테스트 파일 수정 | `test_*.py`, `*_test.py`, `*_test.dart` | #31 | `ALLOW_TEST_EDIT=1` |
| 테스트 파일 삭제 (`rm`/`git rm`) | basename이 `test_*.py`, `*_test.py`, `*_test.dart` | #31 | `ALLOW_TEST_EDIT=1` |
| `--update-goldens` Bash | 명령에 포함 시 | #31 | 없음 |
| `manage.py migrate` / `django-admin migrate` | 토큰 기반 | #25 | `--check`, `--dry-run`은 허용 |
| `git push origin main` | ref 타깃 기반 (best-effort) | GitOps | 없음 |
| `rm -rf` | 경로 무관 | #28 | 없음 |
| `git push --force` / `-f` / `--force-with-lease` | | #28 | 없음 |
| `DROP TABLE` / `TRUNCATE` | SQL, 대소문자 무시 | #28 | 없음 |
| `manage.py flush` | | #28 | 없음 |

**신규 테스트 파일 생성(Write + 미존재 경로)은 항상 허용.**
**conftest.py, factories.py 등 헬퍼 모듈은 basename 기반으로 차단하지 않음.**

#### #28 파괴적 명령 오버라이드 없음

`rm -rf`, `git push --force`, `DROP TABLE`, `TRUNCATE`, `manage.py flush`는
오버라이드 환경변수가 없다. 인간이 직접 셸에서 실행하는 것은 이 hook 밖이므로
Claude Code를 통하지 않으면 차단되지 않는다 — 이것이 의도된 설계다.

### `pre-commit` — git hook (심층 방어)

| 가드 | 대상 | CONSTRAINTS | 오버라이드 |
|------|------|-------------|------------|
| 마이그레이션 staged | `server/.../migrations/*.py` | #25 | `ALLOW_MIGRATIONS=1` |
| 생성 파일 staged | `*.g.dart`, `*.freezed.dart` | #32 | `ALLOW_GENERATED=1` |
| gitleaks 시크릿 스캔 | staged 전체 | #27 | 없음 (CI 최종 게이트) |

---

## 오버라이드 환경변수 (인간 전용)

오버라이드는 팀 리드/인간이 직접 검토 후에만 사용한다.

```sh
# 기존 테스트 수정이 불가피할 때 (guard.py)
ALLOW_TEST_EDIT=1 claude ...

# 마이그레이션 커밋이 불가피할 때 (pre-commit)
ALLOW_MIGRATIONS=1 git commit -m "..."

# 생성 파일 커밋이 불가피할 때 (pre-commit)
ALLOW_GENERATED=1 git commit -m "..."
```

---

## Failure Modes

| 상황 | 동작 | 이유 |
|------|------|------|
| JSON 파싱 실패 | fail-open (exit 0) | 가용성 트레이드오프 — Claude Code는 well-formed JSON을 보장하므로 정상 운영에서는 발생하지 않음 |
| guard.py 스크립트 미존재 | Claude Code가 hook 실패로 처리 | settings.json 절대경로(`${CLAUDE_PROJECT_DIR}`) 사용으로 CWD 우회 방지 |
| gitleaks 미설치 | 경고만 출력, 커밋 허용 | CI gitleaks가 최종 게이트 |
| `echo "DROP TABLE"` 등 문자열 내 SQL 키워드 | fail-safe 과차단(block) | 명령 실행과 문자열을 구별하지 않는다. 파괴적 명령 누락보다 드문 과차단이 안전 — 필요 시 인간이 직접 실행 |
| `rm "$FILE"` / `rm *.dart` 셸 변수·글로브 인자 | 미감지(under-block) | 정적 분석으로 변수·글로브 확장 전 패턴을 확인할 수 없다. 실행 시점 파일명은 hook에 전달되지 않는다 |

---

## 동작 검증

```sh
python3 scripts/hooks/test_hooks.py
# → ALL PASS
```

---

## 근거 (CONSTRAINTS 발췌)

- **#25**: migrations는 makemigrations 명령으로만 생성. 적용은 인간이 검토·승인.
- **#27**: AI는 .env 시크릿에 접근하지 않는다. .env.example로 스키마만 공유.
- **#28**: 파괴적 명령(rm -rf, force push, DROP/TRUNCATE, flush)은 인간 전용. 오버라이드 없음.
- **#31**: 골든 베이스라인·기존 테스트는 인간 승인 없이 변경 불가.
- **#32**: *.g.dart / *.freezed.dart는 build_runner 전용. 손편집 시 build_runner가 덮어씀.
- **GitOps**: main=prod 게이트. dev→main 릴리즈 PR로만 머지.
  브랜치 가드는 best-effort — 권위 게이트는 GitHub 브랜치 보호(현재 무료 플랜이라 미적용 — Pro 시 적용 권장).
