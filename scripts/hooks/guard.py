#!/usr/bin/env python3
"""
guard.py — Claude Code PreToolUse hook for Assen Platform.

목적: 비가역 영역(마이그레이션, 생성 파일, 골든, 시크릿, 기존 테스트)에 대한
     Claude Code 도구 호출을 기계 강제로 차단한다.
     자연어 지시는 보안 경계가 아니다 (CONSTRAINTS #25~#32).

프로토콜:
  - stdin: JSON { tool_name, tool_input: { file_path?, content?, command? } }
  - 차단: exit 2, stderr에 사유 출력 (모델이 읽음)
  - 허용: exit 0

설치: .claude/settings.json hooks 섹션에서 PreToolUse 으로 등록.
"""

import json
import os
import sys


# ---------------------------------------------------------------------------
# 유틸
# ---------------------------------------------------------------------------

def _block(reason: str) -> None:
    """차단 사유를 stderr에 출력하고 exit 2."""
    print(f"[GUARD BLOCKED] {reason}", file=sys.stderr)
    sys.exit(2)


def _is_existing_file(path: str) -> bool:
    """경로가 실제 파일로 존재하는지 확인 (신규 생성 Write와 기존 수정 Edit 구분)."""
    return os.path.isfile(path)


# ---------------------------------------------------------------------------
# 경로 분류 함수
# ---------------------------------------------------------------------------

def _is_migration_path(path: str) -> bool:
    """
    server/**/migrations/**/*.py 패턴.
    fnmatch는 ** 미지원이므로 세그먼트 직접 분석.
    WHY (#25): migrations는 인간 게이트 — makemigrations 명령으로만 생성,
    적용·수정은 인간 승인.
    """
    parts = path.replace("\\", "/").split("/")
    if not parts[0].startswith("server"):
        return False
    if "migrations" not in parts:
        return False
    if not path.endswith(".py"):
        return False
    return True


def _is_generated_file(path: str) -> bool:
    """
    *.g.dart / *.freezed.dart 패턴.
    WHY (#32): 생성 파일 손편집 금지 — build_runner 재실행으로만 변경.
    """
    base = os.path.basename(path)
    return base.endswith(".g.dart") or base.endswith(".freezed.dart")


def _is_golden_path(path: str) -> bool:
    """
    **/goldens/** 또는 *.golden.* 패턴.
    WHY (#31): 골든 베이스라인은 인간 승인.
    """
    norm = path.replace("\\", "/")
    base = os.path.basename(norm)
    if "/goldens/" in norm:
        return True
    if ".golden." in base:
        return True
    return False


def _is_env_secret(path: str) -> bool:
    """
    .env / **/.env / *.env 차단 — 단 .env.example 허용.
    WHY (#27): 시크릿 접근 금지.
    """
    base = os.path.basename(path)
    if base == ".env.example":
        return False
    if base == ".env" or base.endswith(".env"):
        return True
    return False


def _is_test_file(path: str) -> bool:
    """
    **/test/** / **/tests/** / *_test.dart / test_*.py 패턴.
    WHY (#31): 테스트 약화 방지 — 신규 테스트 추가는 자유,
    기존 테스트 변경은 인간 승인(ALLOW_TEST_EDIT=1).
    """
    norm = path.replace("\\", "/")
    base = os.path.basename(norm)
    if "/test/" in norm or "/tests/" in norm:
        return True
    if base.endswith("_test.dart"):
        return True
    if base.startswith("test_") and base.endswith(".py"):
        return True
    return False


# ---------------------------------------------------------------------------
# 파일 경로 기반 규칙 (Write / Edit / MultiEdit / NotebookEdit / Read)
# ---------------------------------------------------------------------------

def check_file_path(tool_name: str, file_path: str) -> None:
    """
    파일 경로를 검사해 차단 여부 결정.
    tool_name: Write | Edit | MultiEdit | NotebookEdit | Read
    """
    # Write + 파일 미존재 = 신규 생성
    is_new_write = (tool_name == "Write") and (not _is_existing_file(file_path))

    # --- #27 시크릿 (.env) — Read 포함 모든 접근 차단
    if _is_env_secret(file_path):
        _block(
            f"#27 시크릿 접근 금지: '{file_path}' — .env 파일은 Claude Code가 읽거나 쓸 수 없습니다. "
            "시크릿이 필요하면 .env.example을 사용하세요."
        )

    # --- #25 마이그레이션 파일 생성·수정 차단
    if _is_migration_path(file_path):
        _block(
            f"#25 마이그레이션 인간 게이트: '{file_path}' — migrations는 "
            "`manage.py makemigrations`으로만 생성하고, 적용·수정은 인간 승인 필요."
        )

    # --- #32 생성 파일 손편집 금지
    if _is_generated_file(file_path):
        _block(
            f"#32 생성 파일 손편집 금지: '{file_path}' — "
            "*.g.dart / *.freezed.dart 는 build_runner가 관리합니다. "
            "소스를 수정 후 `flutter pub run build_runner build`를 실행하세요."
        )

    # --- #31 골든 베이스라인 인간 승인
    if _is_golden_path(file_path):
        _block(
            f"#31 골든 베이스라인 인간 승인 필요: '{file_path}' — "
            "골든 파일은 직접 수정할 수 없습니다. "
            "`--update-goldens` 플래그도 인간이 실행해야 합니다."
        )

    # --- #31 기존 테스트 파일 수정 방지 (신규 생성 Write는 허용)
    if _is_test_file(file_path):
        if is_new_write:
            # 새 테스트 파일 생성은 허용
            return
        # 기존 파일 편집 또는 덮어쓰기 — ALLOW_TEST_EDIT=1 이면 통과
        if os.environ.get("ALLOW_TEST_EDIT") == "1":
            return
        _block(
            f"#31 테스트 약화 방지: '{file_path}' — 기존 테스트 파일 수정은 인간 승인 필요. "
            "새 테스트 추가는 자유. 인간이 검토 후 `ALLOW_TEST_EDIT=1` 환경변수를 설정하면 통과."
        )


# ---------------------------------------------------------------------------
# Bash 명령 기반 규칙
# ---------------------------------------------------------------------------

def check_bash_command(command: str) -> None:
    """Bash 명령 내용을 검사해 차단 여부 결정."""

    # --- #31 --update-goldens 차단
    if "--update-goldens" in command:
        _block(
            "#31 골든 업데이트 차단: `--update-goldens` 플래그는 인간이 직접 실행해야 합니다. "
            "골든 베이스라인 변경은 인간 승인 필요."
        )

    # --- #25 manage.py migrate 차단 (makemigrations / --check / --dry-run 은 허용)
    if "manage.py migrate" in command:
        if "makemigrations" in command:
            return  # makemigrations는 manage.py migrate 문자열을 포함하지 않으나 안전망
        if "--check" in command or "--dry-run" in command:
            return
        _block(
            "#25 마이그레이션 적용 차단: `manage.py migrate`는 스테이징/프로덕션 적용 명령입니다. "
            "인간이 직접 실행해야 합니다. "
            "`manage.py migrate --check` 또는 `manage.py migrate --dry-run`은 허용."
        )

    # --- GitOps: main 직접 push 차단
    if "git push" in command and "origin" in command and "main" in command:
        _block(
            "GitOps 위반: `git push ... origin ... main` — main 브랜치 직접 push 금지. "
            "dev → main 릴리즈 게이트(PR)를 통해서만 머지하세요."
        )


# ---------------------------------------------------------------------------
# 메인
# ---------------------------------------------------------------------------

def main() -> None:
    raw = sys.stdin.read()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        # JSON 파싱 실패 시 통과 — 오탐 방지
        print(f"[GUARD WARNING] JSON 파싱 실패: {e}", file=sys.stderr)
        sys.exit(0)

    tool_name: str = data.get("tool_name", "")
    tool_input: dict = data.get("tool_input", {})

    # --- 파일 경로 기반 도구
    if tool_name in ("Write", "Edit", "MultiEdit", "NotebookEdit", "Read"):
        file_path = tool_input.get("file_path", "")
        if file_path:
            check_file_path(tool_name, file_path)
        # MultiEdit: edits 배열 내 각 파일도 검사
        for edit in tool_input.get("edits", []):
            fp = edit.get("file_path", "")
            if fp:
                check_file_path(tool_name, fp)

    # --- Bash 명령 기반
    elif tool_name == "Bash":
        command: str = tool_input.get("command", "")
        if command:
            check_bash_command(command)

    sys.exit(0)


if __name__ == "__main__":
    main()
