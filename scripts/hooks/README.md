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
| 시크릿 접근 | `.env`, `**/.env`, `*.env` | #27 | 없음 (`.env.example`은 허용) |
| 기존 테스트 파일 수정 | `**/test/**`, `*_test.dart`, `test_*.py` | #31 | `ALLOW_TEST_EDIT=1` |
| `--update-goldens` Bash | 명령에 포함 시 | #31 | 없음 |
| `manage.py migrate` | 명령에 포함 시 | #25 | `--check`, `--dry-run`은 허용 |
| `git push origin main` | 명령에 포함 시 | GitOps | 없음 |

**신규 테스트 파일 생성(Write + 미존재 경로)은 항상 허용.**

### `pre-commit` — git hook (심층 방어)

| 가드 | 대상 | CONSTRAINTS | 오버라이드 |
|------|------|-------------|------------|
| 마이그레이션 staged | `server/.../migrations/*.py` | #25 | `ALLOW_MIGRATIONS=1` |
| 생성 파일 staged | `*.g.dart`, `*.freezed.dart` | #32 | `ALLOW_GENERATED=1` |
| gitleaks 시크릿 스캔 | staged 전체 | #27 | 없음 (CI 최종 게이트) |

---

## 오버라이드 환경변수 (인간 전용)

오버라이드는 팀 리드/인간이 직접 검토 후에만 사용한다.
Claude Code에서 환경변수를 설정하는 것도 guard.py가 차단하지 않으므로 운영 규칙으로 제한한다.

```sh
# 기존 테스트 수정이 불가피할 때 (guard.py)
ALLOW_TEST_EDIT=1 claude ...

# 마이그레이션 커밋이 불가피할 때 (pre-commit)
ALLOW_MIGRATIONS=1 git commit -m "..."

# 생성 파일 커밋이 불가피할 때 (pre-commit)
ALLOW_GENERATED=1 git commit -m "..."
```

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
- **#31**: 골든 베이스라인·기존 테스트는 인간 승인 없이 변경 불가.
- **#32**: *.g.dart / *.freezed.dart는 build_runner 전용. 손편집 시 build_runner가 덮어씀.
- **GitOps**: main=prod 게이트. dev→main 릴리즈 PR로만 머지.
