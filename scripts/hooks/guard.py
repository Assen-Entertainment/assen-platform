#!/usr/bin/env python3
"""
guard.py — Claude Code PreToolUse hook for Assen Platform.

목적: 비가역 영역(마이그레이션, 생성 파일, 골든, 시크릿, 기존 테스트, 파괴적 명령)에 대한
     Claude Code 도구 호출을 기계 강제로 차단한다.
     자연어 지시는 보안 경계가 아니다 (CONSTRAINTS #25~#32).

프로토콜:
  - stdin: JSON { tool_name, tool_input: { file_path?, content?, command? } }
  - 차단: exit 2, stderr에 사유 출력 (모델이 읽음)
  - 허용: exit 0

설치: .claude/settings.json hooks 섹션에서 PreToolUse 으로 등록.

Failure modes:
  - JSON 파싱 실패 시 fail-open (exit 0) — 가용성 트레이드오프.
    악의적 입력이 JSON 파싱을 깨뜨려 hook을 우회할 수 없도록
    Claude Code 자체가 well-formed JSON을 보장한다.
"""

import json
import os
import re
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


def _normalize(path: str) -> str:
    """경로를 정규화: 백슬래시 → 슬래시."""
    return path.replace("\\", "/")


def _collapse_whitespace(s: str) -> str:
    """연속 공백을 단일 공백으로 축약 (명령어 토큰 비교용)."""
    return re.sub(r"\s+", " ", s)


# ---------------------------------------------------------------------------
# 경로 분류 함수
# ---------------------------------------------------------------------------

def _is_migration_path(path: str) -> bool:
    """
    server 세그먼트 + migrations 세그먼트 + .py 확장자.
    WHY (#25): migrations는 인간 게이트 — makemigrations 명령으로만 생성,
    적용·수정은 인간 승인.

    절대경로·../ 우회 방지: 소문자 변환 후 세그먼트 포함 여부만 검사.
    """
    parts = [p.lower() for p in _normalize(path).split("/")]
    return "server" in parts and "migrations" in parts and path.endswith(".py")


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
    norm = _normalize(path)
    base = os.path.basename(norm)
    if "/goldens/" in norm:
        return True
    if ".golden." in base:
        return True
    return False


# 허용 템플릿 파일 (예시·스키마 공유 목적 — 실 시크릿 없음)
_ENV_ALLOWED_SUFFIXES = (".env.example", ".env.sample", ".env.template")

def _is_env_secret(path: str) -> bool:
    """
    .env / **/.env / .env.* 차단.
    허용: .env.example / .env.sample / .env.template
    WHY (#27): 시크릿 접근 금지.
    """
    base = os.path.basename(path)
    if any(base == suf or base.endswith(suf) for suf in _ENV_ALLOWED_SUFFIXES):
        return False
    # .env 정확히 또는 .env. 프리픽스 (예: .env.production, .env.local)
    if base == ".env" or base.startswith(".env."):
        return True
    return False


def _is_test_file(path: str) -> bool:
    """
    basename이 test_*.py / *_test.py / *_test.dart 인 파일만 차단.
    conftest.py, factories.py, 헬퍼 모듈은 자유.
    WHY (#31): 테스트 약화 방지 — 신규 테스트 추가는 자유,
    기존 테스트 변경은 인간 승인(ALLOW_TEST_EDIT=1).
    """
    base = os.path.basename(_normalize(path))
    if base.startswith("test_") and base.endswith(".py"):
        return True
    if base.endswith("_test.py"):
        return True
    if base.endswith("_test.dart"):
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

    # --- #27 시크릿 (.env.*) — Read 포함 모든 접근 차단
    if _is_env_secret(file_path):
        _block(
            f"#27 시크릿 접근 금지: '{file_path}' — .env 파일은 Claude Code가 읽거나 쓸 수 없습니다. "
            "시크릿이 필요하면 .env.example / .env.sample / .env.template을 사용하세요."
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

def _has_migrate_token(cmd_normalized: str) -> bool:
    """
    (manage.py|django-admin) 뒤에 migrate 토큰이 오는 패턴 감지.
    다중 공백 우회 방지를 위해 공백 collapse 후 토큰 검사.
    """
    # "manage.py migrate" 또는 "django-admin migrate"
    return bool(
        re.search(r"(?:manage\.py|django-admin)\s+migrate(?:\s|$)", cmd_normalized)
    )


def _is_main_push(command: str) -> bool:
    """
    ref 타깃 기반 main push 감지 — 원격 이름이 main인 오탐 방지.
    감지 패턴: `:main`, ` main`(끝), `HEAD:main`, `refs/heads/main`
    WHY: best-effort 가드. 권위 게이트는 GitHub 브랜치 보호
    (현재 무료 플랜이라 미적용 — Pro 시 적용 권장).
    """
    if "git push" not in command:
        return False
    # 명확한 main ref 타깃 패턴
    if re.search(r"(?:HEAD:main|refs/heads/main|:main(?:\s|$))", command):
        return True
    # 토큰 분리: push 뒤 마지막 positional 인자가 main 인지
    # "git push <remote> main" 형태 — 끝 토큰이 main
    tokens = command.split()
    try:
        push_idx = tokens.index("push")
    except ValueError:
        return False
    push_args = [t for t in tokens[push_idx + 1:] if not t.startswith("-")]
    # push_args: [remote, refspec] 또는 [remote] 또는 [refspec...]
    # 마지막 인자가 "main" 이고 그 앞이 remote 이름(main이 아닌 것) 일 때만 차단
    if len(push_args) >= 2 and push_args[-1] == "main" and push_args[-2] != "main":
        return True
    return False


def check_bash_command(command: str) -> None:
    """Bash 명령 내용을 검사해 차단 여부 결정."""

    cmd_collapsed = _collapse_whitespace(command)

    # --- #31 --update-goldens 차단
    if "--update-goldens" in command:
        _block(
            "#31 골든 업데이트 차단: `--update-goldens` 플래그는 인간이 직접 실행해야 합니다. "
            "골든 베이스라인 변경은 인간 승인 필요."
        )

    # --- #25 manage.py / django-admin migrate 차단
    #     (makemigrations / --check / --dry-run 은 허용)
    if _has_migrate_token(cmd_collapsed):
        if "--check" in command or "--dry-run" in command:
            pass  # 허용
        else:
            _block(
                "#25 마이그레이션 적용 차단: `manage.py migrate` / `django-admin migrate`는 "
                "스테이징/프로덕션 적용 명령입니다. 인간이 직접 실행해야 합니다. "
                "`--check` 또는 `--dry-run`은 허용."
            )

    # --- #28 파괴적 명령 차단 (오버라이드 없음 — 인간이 직접 셸에서 실행)
    # rm: 재귀 플래그와 강제 플래그가 함께 있으면 차단. 결합(-rf/-fr)이든
    # 분리(-r -f)든, 단/장(--recursive/--force)이든 순서·간격 무관하게 잡는다.
    if re.search(r"\brm\b", command):
        has_recursive = re.search(r"(?:^|\s)-[a-zA-Z]*r|\s--recursive\b", command)
        has_force = re.search(r"(?:^|\s)-[a-zA-Z]*f|\s--force\b", command)
        if has_recursive and has_force:
            _block(
                "#28 파괴적 명령 차단: `rm -rf` — 재귀 강제 삭제는 인간이 직접 셸에서 실행해야 합니다."
            )

    # git push --force / -f / --force-with-lease[=ref] — =value 형태까지 잡는다
    if "git push" in command and (
        re.search(r"(?:^|\s)(?:--force|-f)(?:\s|$)", command)
        or re.search(r"(?:^|\s)--force-with-lease(?:=\S+)?(?:\s|$)", command)
    ):
        _block(
            "#28 파괴적 명령 차단: `git push --force` / `-f` / `--force-with-lease` — "
            "강제 push는 git history를 파괴할 수 있습니다. 인간이 직접 셸에서 실행하세요."
        )

    # SQL DROP TABLE / TRUNCATE (대소문자 무시)
    if re.search(r"\bdrop\s+table\b", command, re.IGNORECASE):
        _block(
            "#28 파괴적 명령 차단: `DROP TABLE` — 테이블 삭제는 인간이 직접 실행해야 합니다."
        )
    if re.search(r"\btruncate\b", command, re.IGNORECASE):
        _block(
            "#28 파괴적 명령 차단: `TRUNCATE` — 테이블 전체 삭제는 인간이 직접 실행해야 합니다."
        )

    # manage.py flush
    if re.search(r"manage\.py\s+flush\b", cmd_collapsed):
        _block(
            "#28 파괴적 명령 차단: `manage.py flush` — DB 전체 초기화는 인간이 직접 실행해야 합니다."
        )

    # --- GitOps: main 직접 push 차단 (best-effort ref 타깃 기반)
    if _is_main_push(command):
        _block(
            "GitOps 위반: main 브랜치 직접 push 금지. "
            "dev → main 릴리즈 게이트(PR)를 통해서만 머지하세요. "
            "브랜치 가드는 best-effort — 권위 게이트는 GitHub 브랜치 보호 규칙."
        )


# ---------------------------------------------------------------------------
# 메인
# ---------------------------------------------------------------------------

def main() -> None:
    raw = sys.stdin.read()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        # JSON 파싱 실패 시 fail-open — 가용성 트레이드오프.
        # Claude Code는 well-formed JSON을 보장하므로 정상 운영 중에는 발생하지 않는다.
        print(f"[GUARD WARNING] JSON 파싱 실패 (fail-open): {e}", file=sys.stderr)
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
        # NotebookEdit: notebook_path fallback
        if tool_name == "NotebookEdit" and not file_path:
            nb_path = tool_input.get("notebook_path", "")
            if nb_path:
                check_file_path(tool_name, nb_path)

    # --- Bash 명령 기반
    elif tool_name == "Bash":
        command: str = tool_input.get("command", "")
        if command:
            check_bash_command(command)

    sys.exit(0)


if __name__ == "__main__":
    main()
