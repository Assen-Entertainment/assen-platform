#!/bin/sh
# install-hooks.sh — Assen Platform git hook 설치 스크립트
#
# 목적: git core.hooksPath를 scripts/hooks로 설정해
#       pre-commit 등 모든 hook을 버전 관리 하에 둔다.
#
# 사용: sh scripts/install-hooks.sh
#       (레포 루트에서 실행)

set -e

REPO_ROOT="$(git rev-parse --show-toplevel)"
HOOKS_DIR="${REPO_ROOT}/scripts/hooks"

if [ ! -d "${HOOKS_DIR}" ]; then
    echo "[ERROR] scripts/hooks 디렉터리를 찾을 수 없습니다: ${HOOKS_DIR}" >&2
    exit 1
fi

# 실행 권한 보장 (scripts/hooks/ 아래 모든 실행 파일)
# 워크트리에서 체크아웃해도 권한이 유지되도록 전체 적용
chmod +x "${HOOKS_DIR}"/*

# git hook 경로 설정 (로컬 레포 설정 — 워크트리 공유됨)
# NOTE: git worktree는 core.hooksPath를 공유하므로 각 워크트리에서 재실행 불필요
git config core.hooksPath scripts/hooks

echo "[OK] git hook 설치 완료: core.hooksPath = scripts/hooks"
echo "     pre-commit hook이 활성화되었습니다."
echo ""
echo "  포함된 가드:"
echo "    #31 기존 테스트 파일 수정/삭제 차단 (ALLOW_TEST_EDIT=1 으로 오버라이드)"
echo "    #25 마이그레이션 파일 커밋 차단     (ALLOW_MIGRATIONS=1 으로 오버라이드)"
echo "    #31 골든 파일 커밋 차단             (ALLOW_GOLDEN=1 으로 오버라이드)"
echo "    #27 .env 시크릿 파일 커밋 차단      (오버라이드 없음 — 절대 커밋 금지)"
echo "    #32 생성 파일 커밋 차단             (ALLOW_GENERATED=1 으로 오버라이드)"
echo "    #27 gitleaks 시크릿 스캔            (~/bin-tools/gitleaks 필요)"
