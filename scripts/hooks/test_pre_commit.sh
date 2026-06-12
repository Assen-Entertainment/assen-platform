#!/bin/sh
# test_pre_commit.sh — pre-commit hook 행위 검증 (샌드박스 git repo)
#
# 목적: pre-commit 차단 규칙을 임시 git repo에서 실제 커밋 시나리오로 검증한다.
#       guard.py(Python/Claude Code 계층)와 별도로, git hook 계층만 단독 실증.
#
# 실행: bash scripts/hooks/test_pre_commit.sh
#       → "ALL PASS" 출력 시 전 케이스 green.
#
# CI: .github/workflows/ci.yml 의 hooks 잡에서 실행됨.

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PRE_COMMIT="${SCRIPT_DIR}/pre-commit"

RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m'

PASS=0
FAIL=0

# ---------------------------------------------------------------------------
# 헬퍼
# ---------------------------------------------------------------------------

# 임시 git repo를 초기화하고 pre-commit hook을 설치한다.
# 사용 후 tmpdir 변수로 디렉터리를 참조한다.
setup_repo() {
    tmpdir="$(mktemp -d)"
    git -C "${tmpdir}" init -q
    git -C "${tmpdir}" config user.email "test@example.com"
    git -C "${tmpdir}" config user.name "Test"
    # pre-commit hook 직접 설치 (core.hooksPath 불필요 — .git/hooks 직접 복사)
    cp "${PRE_COMMIT}" "${tmpdir}/.git/hooks/pre-commit"
    chmod +x "${tmpdir}/.git/hooks/pre-commit"
    # 초기 커밋 (빈 repo는 HEAD 없어서 일부 git 명령 실패)
    printf "init\n" > "${tmpdir}/README.md"
    git -C "${tmpdir}" add README.md
    git -C "${tmpdir}" commit -q -m "init"
}

teardown_repo() {
    rm -rf "${tmpdir}"
}

# stage_file <relative-path> <content>
stage_file() {
    local path="${tmpdir}/$1"
    mkdir -p "$(dirname "${path}")"
    printf '%s' "$2" > "${path}"
    git -C "${tmpdir}" add "$1"
}

# stage_modify <relative-path> <new-content>
# 기존 파일을 수정한다. 파일이 없으면 먼저 커밋해둔다.
stage_modify() {
    local path="${tmpdir}/$1"
    mkdir -p "$(dirname "${path}")"
    # 파일이 아직 없으면 초기 버전을 커밋 (M 상태로 만들기 위해)
    if [ ! -f "${path}" ]; then
        printf "original\n" > "${path}"
        git -C "${tmpdir}" add "$1"
        git -C "${tmpdir}" commit -q -m "add $1"
    fi
    printf '%s\n' "$2" > "${path}"
    git -C "${tmpdir}" add "$1"
}

# stage_delete <relative-path>
stage_delete() {
    local path="${tmpdir}/$1"
    # 파일이 없으면 먼저 커밋
    if [ ! -f "${path}" ]; then
        mkdir -p "$(dirname "${path}")"
        printf "original\n" > "${path}"
        git -C "${tmpdir}" add "$1"
        git -C "${tmpdir}" commit -q -m "add $1"
    fi
    git -C "${tmpdir}" rm -f -q "$1"
}

# try_commit [env_overrides...]  → returns exit code of git commit
try_commit() {
    env "$@" git -C "${tmpdir}" commit -m "test commit" 2>/tmp/pc_stderr_$$
    return $?
}

assert_blocked() {
    name="$1"
    shift
    if env "$@" git -C "${tmpdir}" commit -m "test commit" >/dev/null 2>/tmp/pc_stderr_$$; then
        printf "${RED}  [FAIL]${NC} %s — 차단되어야 하나 커밋 성공\n" "${name}"
        FAIL=$((FAIL + 1))
    else
        # stderr에 [PRE-COMMIT BLOCKED] 또는 커밋 거부됨 포함 여부 확인
        if grep -qE '\[PRE-COMMIT BLOCKED\]|커밋 거부됨' /tmp/pc_stderr_$$ 2>/dev/null; then
            printf "${GREEN}  [PASS]${NC} %s\n" "${name}"
            PASS=$((PASS + 1))
        else
            printf "${RED}  [FAIL]${NC} %s — 거부됐지만 예상 메시지 없음\n" "${name}"
            cat /tmp/pc_stderr_$$ >&2
            FAIL=$((FAIL + 1))
        fi
    fi
    rm -f /tmp/pc_stderr_$$
    # staged 변경사항 정리 (다음 케이스 오염 방지)
    git -C "${tmpdir}" reset -q HEAD 2>/dev/null || true
    git -C "${tmpdir}" checkout -q -- . 2>/dev/null || true
    git -C "${tmpdir}" clean -q -fd 2>/dev/null || true
}

assert_allowed() {
    name="$1"
    shift
    if env "$@" git -C "${tmpdir}" commit -m "test commit" >/dev/null 2>/tmp/pc_stderr_$$; then
        printf "${GREEN}  [PASS]${NC} %s\n" "${name}"
        PASS=$((PASS + 1))
    else
        printf "${RED}  [FAIL]${NC} %s — 허용되어야 하나 차단됨\n" "${name}"
        cat /tmp/pc_stderr_$$ >&2
        FAIL=$((FAIL + 1))
    fi
    rm -f /tmp/pc_stderr_$$
    # staged 변경사항 정리
    git -C "${tmpdir}" reset -q HEAD 2>/dev/null || true
    git -C "${tmpdir}" checkout -q -- . 2>/dev/null || true
    git -C "${tmpdir}" clean -q -fd 2>/dev/null || true
}

# ---------------------------------------------------------------------------
# 케이스 1: #31 기존 테스트 파일 수정 차단
# ---------------------------------------------------------------------------
printf "\n[케이스 1] #31 기존 테스트 파일 수정 차단\n"
setup_repo
stage_modify "server/tests/test_auth.py" "modified"
assert_blocked "#31 test_*.py 수정 M 차단"
teardown_repo

# ---------------------------------------------------------------------------
# 케이스 2: #31 기존 테스트 파일 삭제 차단
# ---------------------------------------------------------------------------
printf "\n[케이스 2] #31 기존 테스트 파일 삭제 차단\n"
setup_repo
stage_delete "apps/mobile/test/widget_test.dart"
assert_blocked "#31 *_test.dart 삭제 D 차단"
teardown_repo

# ---------------------------------------------------------------------------
# 케이스 3: #31 *_test.py 수정 차단
# ---------------------------------------------------------------------------
printf "\n[케이스 3] #31 *_test.py 수정 차단\n"
setup_repo
stage_modify "server/tests/auth_test.py" "modified"
assert_blocked "#31 *_test.py 수정 차단"
teardown_repo

# ---------------------------------------------------------------------------
# 케이스 4: ALLOW_TEST_EDIT=1 기존 테스트 수정 통과
# ---------------------------------------------------------------------------
printf "\n[케이스 4] ALLOW_TEST_EDIT=1 기존 테스트 수정 통과\n"
setup_repo
stage_modify "server/tests/test_auth.py" "modified with override"
assert_allowed "ALLOW_TEST_EDIT=1 수정 통과" ALLOW_TEST_EDIT=1
teardown_repo

# ---------------------------------------------------------------------------
# 케이스 5: #31 신규 테스트 파일 추가(A)는 자유
# ---------------------------------------------------------------------------
printf "\n[케이스 5] #31 신규 테스트 파일 추가(A)는 자유\n"
setup_repo
stage_file "server/tests/test_new_feature.py" "def test_ok(): pass"
assert_allowed "#31 신규 test_*.py 추가(A) 허용"
teardown_repo

# ---------------------------------------------------------------------------
# 케이스 6: #25 마이그레이션 파일 커밋 차단
# ---------------------------------------------------------------------------
printf "\n[케이스 6] #25 마이그레이션 파일 커밋 차단\n"
setup_repo
stage_file "server/core/migrations/0001_initial.py" "# migration"
assert_blocked "#25 migrations/*.py 차단"
teardown_repo

# ---------------------------------------------------------------------------
# 케이스 7: ALLOW_MIGRATIONS=1 마이그레이션 통과
# ---------------------------------------------------------------------------
printf "\n[케이스 7] ALLOW_MIGRATIONS=1 마이그레이션 통과\n"
setup_repo
stage_file "server/core/migrations/0001_initial.py" "# migration"
assert_allowed "ALLOW_MIGRATIONS=1 통과" ALLOW_MIGRATIONS=1
teardown_repo

# ---------------------------------------------------------------------------
# 케이스 8: #31 골든 파일 커밋 차단 (/goldens/ 경로)
# ---------------------------------------------------------------------------
printf "\n[케이스 8] #31 골든 파일 커밋 차단\n"
setup_repo
stage_file "apps/mobile/test/goldens/login_screen.png" "binary"
assert_blocked "#31 goldens/ 경로 차단"
teardown_repo

# ---------------------------------------------------------------------------
# 케이스 9: ALLOW_GOLDEN=1 골든 파일 통과
# ---------------------------------------------------------------------------
printf "\n[케이스 9] ALLOW_GOLDEN=1 골든 파일 통과\n"
setup_repo
stage_file "apps/mobile/test/goldens/login_screen.png" "binary"
assert_allowed "ALLOW_GOLDEN=1 통과" ALLOW_GOLDEN=1
teardown_repo

# ---------------------------------------------------------------------------
# 케이스 10: #27 .env 파일 커밋 차단
# ---------------------------------------------------------------------------
printf "\n[케이스 10] #27 .env 파일 커밋 차단\n"
setup_repo
stage_file ".env" "SECRET=abc123"
assert_blocked "#27 .env 차단"
teardown_repo

# ---------------------------------------------------------------------------
# 케이스 11: #27 .env.production 커밋 차단
# ---------------------------------------------------------------------------
printf "\n[케이스 11] #27 .env.production 차단\n"
setup_repo
stage_file "server/.env.production" "DB_PASS=secret"
assert_blocked "#27 .env.production 차단"
teardown_repo

# ---------------------------------------------------------------------------
# 케이스 12: #27 .env.example 허용
# ---------------------------------------------------------------------------
printf "\n[케이스 12] #27 .env.example 허용\n"
setup_repo
stage_file ".env.example" "SECRET=changeme"
assert_allowed "#27 .env.example 허용"
teardown_repo

# ---------------------------------------------------------------------------
# 케이스 13: 비대상 일반 파일 커밋 허용
# ---------------------------------------------------------------------------
printf "\n[케이스 13] 비대상 일반 파일 커밋 허용\n"
setup_repo
stage_file "server/core/models.py" "class User: pass"
assert_allowed "일반 소스 파일 허용"
teardown_repo

# ---------------------------------------------------------------------------
# 케이스 14: #31 *.golden.* 파일명 차단
# ---------------------------------------------------------------------------
printf "\n[케이스 14] #31 *.golden.* 파일명 차단\n"
setup_repo
stage_file "test/login_screen.golden.png" "binary"
assert_blocked "#31 .golden. 파일명 차단"
teardown_repo

# ---------------------------------------------------------------------------
# 케이스 15: #27 .env.sample 허용 / #27 .env.template 허용
# ---------------------------------------------------------------------------
printf "\n[케이스 15] #27 .env.sample 허용\n"
setup_repo
stage_file ".env.sample" "DB_URL=postgres://localhost/db"
assert_allowed "#27 .env.sample 허용"
teardown_repo

# ---------------------------------------------------------------------------
# 결과 요약
# ---------------------------------------------------------------------------
printf "\n%s\n" "========================================"
printf "결과: %d passed, %d failed\n" "${PASS}" "${FAIL}"
if [ "${FAIL}" = "0" ]; then
    printf "${GREEN}ALL PASS${NC}\n"
    exit 0
else
    printf "${RED}SOME TESTS FAILED${NC}\n"
    exit 1
fi
