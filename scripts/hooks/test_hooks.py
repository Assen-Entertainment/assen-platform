#!/usr/bin/env python3
"""
test_hooks.py — guard.py 및 pre-commit hook 동작 검증 테스트.

목적: 각 차단 케이스와 허용 케이스를 자동 검증한다.
     pytest 불요 — 순수 python3 표준 라이브러리, assert 기반.

실행: python3 scripts/hooks/test_hooks.py
     → "ALL PASS" 출력 시 전 케이스 green.
"""

import json
import os
import subprocess
import sys
import tempfile

# guard.py 경로 (이 파일과 같은 디렉터리)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
GUARD_SCRIPT = os.path.join(SCRIPT_DIR, "guard.py")
PRE_COMMIT_SCRIPT = os.path.join(SCRIPT_DIR, "pre-commit")
PYTHON = sys.executable

PASS_COUNT = 0
FAIL_COUNT = 0


# ---------------------------------------------------------------------------
# 헬퍼
# ---------------------------------------------------------------------------

def run_guard(payload: dict, env: dict | None = None) -> subprocess.CompletedProcess:
    """guard.py에 JSON payload를 stdin으로 주입해 실행."""
    merged_env = os.environ.copy()
    if env:
        merged_env.update(env)
    return subprocess.run(
        [PYTHON, GUARD_SCRIPT],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        env=merged_env,
    )


def assert_blocked(test_name: str, payload: dict, env: dict | None = None) -> None:
    """exit 2 + stderr에 사유가 있어야 한다."""
    global PASS_COUNT, FAIL_COUNT
    result = run_guard(payload, env)
    if result.returncode == 2 and result.stderr.strip():
        print(f"  [PASS] {test_name}")
        PASS_COUNT += 1
    else:
        print(f"  [FAIL] {test_name}")
        print(f"         exit={result.returncode}, stderr={result.stderr!r}")
        FAIL_COUNT += 1


def assert_allowed(test_name: str, payload: dict, env: dict | None = None) -> None:
    """exit 0이어야 한다."""
    global PASS_COUNT, FAIL_COUNT
    result = run_guard(payload, env)
    if result.returncode == 0:
        print(f"  [PASS] {test_name}")
        PASS_COUNT += 1
    else:
        print(f"  [FAIL] {test_name}")
        print(f"         exit={result.returncode}, stderr={result.stderr!r}")
        FAIL_COUNT += 1


# ---------------------------------------------------------------------------
# guard.py 차단 케이스
# ---------------------------------------------------------------------------

def test_blocked_cases():
    print("\n[guard.py 차단 케이스]")

    # #25 마이그레이션 파일 Write
    assert_blocked(
        "#25 마이그레이션 Write",
        {
            "tool_name": "Write",
            "tool_input": {
                "file_path": "server/core/migrations/0001_initial.py",
                "content": "# migration",
            },
        },
    )

    # #25 마이그레이션 파일 Edit
    assert_blocked(
        "#25 마이그레이션 Edit",
        {
            "tool_name": "Edit",
            "tool_input": {
                "file_path": "server/users/migrations/0002_add_field.py",
                "old_string": "old",
                "new_string": "new",
            },
        },
    )

    # #25 마이그레이션 절대경로 우회 시도
    assert_blocked(
        "#25 마이그레이션 절대경로",
        {
            "tool_name": "Edit",
            "tool_input": {
                "file_path": "/home/user/project/server/core/migrations/0001_initial.py",
                "old_string": "x",
                "new_string": "y",
            },
        },
    )

    # #32 *.g.dart 수정
    assert_blocked(
        "#32 *.g.dart Edit",
        {
            "tool_name": "Edit",
            "tool_input": {
                "file_path": "apps/mobile/lib/models/user.g.dart",
                "old_string": "old",
                "new_string": "new",
            },
        },
    )

    # #32 *.freezed.dart 수정
    assert_blocked(
        "#32 *.freezed.dart Write",
        {
            "tool_name": "Write",
            "tool_input": {
                "file_path": "apps/mobile/lib/models/product.freezed.dart",
                "content": "// freezed",
            },
        },
    )

    # #31 골든 파일 수정 (/goldens/ 경로)
    assert_blocked(
        "#31 goldens 경로 Edit",
        {
            "tool_name": "Edit",
            "tool_input": {
                "file_path": "apps/mobile/test/goldens/login_screen.png",
                "old_string": "x",
                "new_string": "y",
            },
        },
    )

    # #31 골든 파일 수정 (.golden. 포함 파일명)
    assert_blocked(
        "#31 .golden. 파일명 Write",
        {
            "tool_name": "Write",
            "tool_input": {
                "file_path": "apps/mobile/test/login_screen.golden.png",
                "content": "data",
            },
        },
    )

    # #27 .env Read
    assert_blocked(
        "#27 .env Read",
        {
            "tool_name": "Read",
            "tool_input": {"file_path": ".env"},
        },
    )

    # #27 .env Write
    assert_blocked(
        "#27 .env Write",
        {
            "tool_name": "Write",
            "tool_input": {"file_path": ".env", "content": "SECRET=x"},
        },
    )

    # #27 server/.env Read
    assert_blocked(
        "#27 server/.env Read",
        {
            "tool_name": "Read",
            "tool_input": {"file_path": "server/.env"},
        },
    )

    # #27 .env.production Read (프리픽스 구멍 수정 검증)
    assert_blocked(
        "#27 .env.production Read",
        {
            "tool_name": "Read",
            "tool_input": {"file_path": ".env.production"},
        },
    )

    # #27 .env.local Write
    assert_blocked(
        "#27 .env.local Write",
        {
            "tool_name": "Write",
            "tool_input": {"file_path": "server/.env.local", "content": "DB_PASS=x"},
        },
    )

    # #31 기존 테스트 Edit (*_test.dart)
    assert_blocked(
        "#31 기존 테스트 Edit (*_test.dart)",
        {
            "tool_name": "Edit",
            "tool_input": {
                "file_path": "apps/mobile/lib/widget_test.dart",
                "old_string": "x",
                "new_string": "y",
            },
        },
    )

    # #31 기존 테스트 Edit (test_*.py)
    assert_blocked(
        "#31 기존 테스트 Edit (test_*.py)",
        {
            "tool_name": "Edit",
            "tool_input": {
                "file_path": "server/tests/test_auth.py",
                "old_string": "assert True",
                "new_string": "pass",
            },
        },
    )

    # #31 기존 테스트 Edit (*_test.py)
    assert_blocked(
        "#31 기존 테스트 Edit (*_test.py)",
        {
            "tool_name": "Edit",
            "tool_input": {
                "file_path": "server/tests/auth_test.py",
                "old_string": "assert True",
                "new_string": "pass",
            },
        },
    )

    # #31 --update-goldens Bash
    assert_blocked(
        "#31 --update-goldens Bash",
        {
            "tool_name": "Bash",
            "tool_input": {"command": "flutter test --update-goldens"},
        },
    )

    # #25 manage.py migrate Bash
    assert_blocked(
        "#25 manage.py migrate Bash",
        {
            "tool_name": "Bash",
            "tool_input": {"command": "python manage.py migrate"},
        },
    )

    # #25 django-admin migrate 차단 (NEW)
    assert_blocked(
        "#25 django-admin migrate Bash",
        {
            "tool_name": "Bash",
            "tool_input": {"command": "django-admin migrate --settings=config.settings.prod"},
        },
    )

    # GitOps main push 차단
    assert_blocked(
        "GitOps git push origin main",
        {
            "tool_name": "Bash",
            "tool_input": {"command": "git push origin main"},
        },
    )

    # GitOps HEAD:main push 차단
    assert_blocked(
        "GitOps git push origin HEAD:main",
        {
            "tool_name": "Bash",
            "tool_input": {"command": "git push origin HEAD:main"},
        },
    )

    # #28 rm -rf 차단 (NEW)
    assert_blocked(
        "#28 rm -rf 차단",
        {
            "tool_name": "Bash",
            "tool_input": {"command": "rm -rf /tmp/build"},
        },
    )

    # #28 rm -fr 차단 (NEW)
    assert_blocked(
        "#28 rm -fr 차단",
        {
            "tool_name": "Bash",
            "tool_input": {"command": "rm -fr node_modules"},
        },
    )

    # #28 git push --force 차단 (NEW)
    assert_blocked(
        "#28 git push --force 차단",
        {
            "tool_name": "Bash",
            "tool_input": {"command": "git push --force origin feature/x"},
        },
    )

    # #28 git push -f 차단 (NEW)
    assert_blocked(
        "#28 git push -f 차단",
        {
            "tool_name": "Bash",
            "tool_input": {"command": "git push -f origin feature/x"},
        },
    )

    # #28 git push --force-with-lease 차단 (NEW)
    assert_blocked(
        "#28 git push --force-with-lease 차단",
        {
            "tool_name": "Bash",
            "tool_input": {"command": "git push --force-with-lease origin feature/x"},
        },
    )

    # #28 DROP TABLE 차단 (NEW)
    assert_blocked(
        "#28 DROP TABLE 차단",
        {
            "tool_name": "Bash",
            "tool_input": {"command": "psql -c 'DROP TABLE users;'"},
        },
    )

    # #28 TRUNCATE 차단 (NEW)
    assert_blocked(
        "#28 TRUNCATE 차단",
        {
            "tool_name": "Bash",
            "tool_input": {"command": "psql -c 'TRUNCATE orders;'"},
        },
    )

    # #28 manage.py flush 차단 (NEW)
    assert_blocked(
        "#28 manage.py flush 차단",
        {
            "tool_name": "Bash",
            "tool_input": {"command": "python manage.py flush --no-input"},
        },
    )


# ---------------------------------------------------------------------------
# guard.py 허용 케이스
# ---------------------------------------------------------------------------

def test_allowed_cases():
    print("\n[guard.py 허용 케이스]")

    # 일반 소스 파일 Write
    assert_allowed(
        "일반 소스 Write",
        {
            "tool_name": "Write",
            "tool_input": {
                "file_path": "server/core/models.py",
                "content": "class User: pass",
            },
        },
    )

    # .env.example 허용
    assert_allowed(
        ".env.example Write",
        {
            "tool_name": "Write",
            "tool_input": {
                "file_path": ".env.example",
                "content": "SECRET=changeme",
            },
        },
    )

    # .env.sample 허용 (NEW)
    assert_allowed(
        ".env.sample Write",
        {
            "tool_name": "Write",
            "tool_input": {
                "file_path": ".env.sample",
                "content": "DB_URL=postgres://localhost/db",
            },
        },
    )

    # .env.template 허용 (NEW)
    assert_allowed(
        ".env.template Read",
        {
            "tool_name": "Read",
            "tool_input": {"file_path": ".env.template"},
        },
    )

    # 신규 테스트 파일 생성 (Write + 존재하지 않는 경로 → 허용)
    assert_allowed(
        "신규 테스트 파일 Write (미존재)",
        {
            "tool_name": "Write",
            "tool_input": {
                "file_path": "/tmp/assen_test_nonexistent_12345/test_new_feature.py",
                "content": "def test_ok(): pass",
            },
        },
    )

    # conftest.py 수정 허용 (NEW — basename 기반 차단 이후 헬퍼는 자유)
    assert_allowed(
        "conftest.py Edit 허용",
        {
            "tool_name": "Edit",
            "tool_input": {
                "file_path": "server/tests/conftest.py",
                "old_string": "fixture",
                "new_string": "fixture_v2",
            },
        },
    )

    # factories.py 수정 허용 (NEW)
    assert_allowed(
        "factories.py Edit 허용",
        {
            "tool_name": "Edit",
            "tool_input": {
                "file_path": "server/tests/factories.py",
                "old_string": "x",
                "new_string": "y",
            },
        },
    )

    # makemigrations --check 허용
    assert_allowed(
        "makemigrations --check Bash",
        {
            "tool_name": "Bash",
            "tool_input": {"command": "python manage.py makemigrations --check"},
        },
    )

    # manage.py migrate --check 허용
    assert_allowed(
        "manage.py migrate --check Bash",
        {
            "tool_name": "Bash",
            "tool_input": {"command": "python manage.py migrate --check"},
        },
    )

    # manage.py migrate --dry-run 허용
    assert_allowed(
        "manage.py migrate --dry-run Bash",
        {
            "tool_name": "Bash",
            "tool_input": {"command": "python manage.py migrate --dry-run"},
        },
    )

    # ALLOW_TEST_EDIT=1 오버라이드
    assert_allowed(
        "ALLOW_TEST_EDIT=1 기존 테스트 Edit",
        {
            "tool_name": "Edit",
            "tool_input": {
                "file_path": "server/tests/test_auth.py",
                "old_string": "assert True",
                "new_string": "assert result is True",
            },
        },
        env={"ALLOW_TEST_EDIT": "1"},
    )

    # git push origin dev (main 아님 — 허용)
    assert_allowed(
        "git push origin dev (main 아님)",
        {
            "tool_name": "Bash",
            "tool_input": {"command": "git push origin dev"},
        },
    )

    # git push main dev — 원격 이름이 main, 브랜치가 dev (오탐 방지, NEW)
    assert_allowed(
        "git push main dev (remote=main, branch=dev)",
        {
            "tool_name": "Bash",
            "tool_input": {"command": "git push main dev"},
        },
    )

    # 일반 flutter test (--update-goldens 없음)
    assert_allowed(
        "flutter test (goldens 없음)",
        {
            "tool_name": "Bash",
            "tool_input": {"command": "flutter test --coverage"},
        },
    )

    # git push --force 없는 일반 push
    assert_allowed(
        "git push origin feature/x (force 없음)",
        {
            "tool_name": "Bash",
            "tool_input": {"command": "git push origin feature/x"},
        },
    )


# ---------------------------------------------------------------------------
# pre-commit hook 통합 테스트 (임시 git repo)
# ---------------------------------------------------------------------------

def test_pre_commit_migration_block():
    """
    임시 git repo를 만들어 마이그레이션 파일 staged 커밋이 거부되는지 실제 실행 단언.
    WHY: Claude Code hook은 Claude Code 밖에서 우회 가능하므로 git hook도 검증.
    """
    global PASS_COUNT, FAIL_COUNT
    print("\n[pre-commit 통합 테스트]")

    with tempfile.TemporaryDirectory() as tmpdir:
        # 임시 git repo 초기화
        subprocess.run(["git", "init"], cwd=tmpdir, capture_output=True, check=True)
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=tmpdir, capture_output=True, check=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test"],
            cwd=tmpdir, capture_output=True, check=True,
        )
        # hook 경로 설정 — pre-commit 스크립트를 직접 가리킴
        hooks_tmp = os.path.join(tmpdir, ".git", "hooks")
        import shutil
        shutil.copy(PRE_COMMIT_SCRIPT, os.path.join(hooks_tmp, "pre-commit"))
        os.chmod(os.path.join(hooks_tmp, "pre-commit"), 0o755)

        # 초기 커밋 (빈 파일)
        init_file = os.path.join(tmpdir, "README.md")
        with open(init_file, "w") as f:
            f.write("init")
        subprocess.run(["git", "add", "README.md"], cwd=tmpdir, capture_output=True, check=True)
        subprocess.run(
            ["git", "commit", "-m", "init"],
            cwd=tmpdir, capture_output=True, check=True,
        )

        # 마이그레이션 파일 생성 + stage
        mig_dir = os.path.join(tmpdir, "server", "core", "migrations")
        os.makedirs(mig_dir, exist_ok=True)
        mig_file = os.path.join(mig_dir, "0001_initial.py")
        with open(mig_file, "w") as f:
            f.write("# migration")
        subprocess.run(
            ["git", "add", mig_file],
            cwd=tmpdir, capture_output=True, check=True,
        )

        # 커밋 시도 — 차단되어야 함
        result = subprocess.run(
            ["git", "commit", "-m", "add migration"],
            cwd=tmpdir, capture_output=True, text=True,
        )
        if result.returncode != 0 and "마이그레이션" in result.stderr:
            print("  [PASS] pre-commit: 마이그레이션 staged 커밋 거부")
            PASS_COUNT += 1
        else:
            print("  [FAIL] pre-commit: 마이그레이션 staged 커밋이 거부되지 않음")
            print(f"         exit={result.returncode}, stderr={result.stderr!r}")
            FAIL_COUNT += 1

        # ALLOW_MIGRATIONS=1 오버라이드 — 커밋 성공해야 함
        env_override = os.environ.copy()
        env_override["ALLOW_MIGRATIONS"] = "1"
        result2 = subprocess.run(
            ["git", "commit", "-m", "add migration (override)"],
            cwd=tmpdir, capture_output=True, text=True,
            env=env_override,
        )
        if result2.returncode == 0:
            print("  [PASS] pre-commit: ALLOW_MIGRATIONS=1 오버라이드 커밋 성공")
            PASS_COUNT += 1
        else:
            print("  [FAIL] pre-commit: ALLOW_MIGRATIONS=1 오버라이드 실패")
            print(f"         exit={result2.returncode}, stderr={result2.stderr!r}")
            FAIL_COUNT += 1


# ---------------------------------------------------------------------------
# 진입점
# ---------------------------------------------------------------------------

def main():
    print("=== Assen Platform Hook 동작 검증 ===")
    print(f"guard.py : {GUARD_SCRIPT}")
    print(f"pre-commit: {PRE_COMMIT_SCRIPT}")

    test_blocked_cases()
    test_allowed_cases()
    test_pre_commit_migration_block()

    print(f"\n{'='*40}")
    print(f"결과: {PASS_COUNT} passed, {FAIL_COUNT} failed")
    if FAIL_COUNT == 0:
        print("ALL PASS")
        sys.exit(0)
    else:
        print("SOME TESTS FAILED")
        sys.exit(1)


if __name__ == "__main__":
    main()
