# AGENTS.md — Assen Platform

> ⚠️ **방향 전환(2026-06-30):** 현행 제품 = 범용·서브컬쳐 **크리에이터-팬 플랫폼**. 신방향 정본은 `Company-OS/02_Product/SDLC/08(웹)·09(백엔드)·10(모바일)` — 웹=React+Next(`web/`), 모바일=Flutter, 백엔드 신규 도메인 5앱(creator·social·content·commerce·membership). 아래 메이드카페 서술은 구방향(아카이브 예정) 기록이다. 게이트 원칙(가격/정산/약관/본인인증/IAP/결제/migrate = 대표·법무)은 신방향에도 동일 적용.

Assen Platform: 메이드카페 '하츠코이'의 오프라인 경험을 온라인으로 잇는 크로스플랫폼 서비스. *(구방향)*
Flutter(web+iOS+Android) + Django 5.2 LTS + Django Ninja. P0는 Fan CRM이다 — 팬덤 수익화 기능(P1/P2)은 feature flag off로 시작한다.

## 필수 선행 문서

작업 전 반드시 읽는다 (상위 `/mnt/c/Users/daisy/Assen/AGENTS.md`의 Company-OS 참조 의무 포함):

1. `docs/CONSTRAINTS.md` — 이 repo의 제약사항 41개 (사업/IAP, 컴플라이언스, 아키텍처, 하네스)
2. `Company-OS/03_Engineering/Development_Constraints.md` — 권한 경계와 blocker 기준
3. `Company-OS/07_LLM/LLM_Harness_Index.md` — LLM 사용 gate
4. 아키텍처 배경: `Company-OS/03_Engineering/Assen_Platform_Technical_Architecture.md` + `docs/adr/`

## 권한 경계 (요약)

- 에이전트가 결정 가능: 코드 구조, 테스트 전략, 검증 명령, 모듈 경계.
- 인간 승인 필수: 결제·과금 로직, 인증/권한 코드, migrations 적용, 골든 파일 갱신, 테스트 수정, 프로덕션 관련 일체.
- 단독 확정 불가 (Company-OS): 가격, 정산, 개인정보 문구, 캐스트 동의, 오픈일, 외부 공개 수치.

## 검증 계약 (ASS-81 scaffold 완료 — 실제 명령)

Flutter는 pub workspace + Melos 7. 스크립트는 루트 `pubspec.yaml`의 `melos:` 블록에 있고 CI도 동일 명령을 쓴다. 스택별 상세·개별 테스트 명령은 `apps/AGENTS.md`, `server/AGENTS.md` 참조.

- Flutter (repo 루트): `dart pub get` → `dart run melos run format` → `dart run melos run analyze` → `dart run melos run test`
  - 개별 파일: `flutter test packages/<pkg>/test/<file>_test.dart`
  - 빌드 스모크(CI): `flutter build web` · `flutter build apk --debug` (fan_app). iOS는 macOS 비용 10x라 주간 cron/수동 dispatch만.
- Django (`server/`): `uv sync` → `uv run ruff check .` → `uv run mypy .` → `uv run pytest` → `uv run python manage.py makemigrations --check --dry-run --settings=config.settings.test`
  - 개별 테스트: `uv run pytest apps/<domain>/tests/test_smoke.py::<name>`
- docker compose는 로컬 부재 → CI에서 `docker compose config -q` + postgres/redis/celery-worker 기동 스모크로 검증.
- 완료 주장에는 증거(테스트 출력/빌드 로그/스크린샷)를 첨부한다. 작성 세션이 자체 승인하지 않는다.

## 클론 후 필수 1회 실행

```sh
sh scripts/install-hooks.sh   # git pre-commit hook 활성화 (core.hooksPath=scripts/hooks)
```

부모 디렉터리 세션·에이전트 worktree에서는 guard.py(Claude Code hook)가 inert하므로
git pre-commit이 유일 방어 계층이다. 계층별 적용 범위는 `scripts/hooks/README.md` 참조.

## 하지 말 것 (사고 다발 영역)

- `*.g.dart` / `*.freezed.dart` 직접 편집 (build_runner 재실행)
- `flutter test --update-goldens` 자율 실행
- migrations 파일 수정·적용, 테스트 약화·삭제
- 한국 iOS 앱 코드/카피에 웹 결제 유도 삽입 (anti-steering 위반)
- Riverpod 2.x 문법 사용 (이 repo는 3.x)
- `.env`·크레덴셜 읽기/커밋

## GitOps (브랜치·배포 계약 — 2026-06-12 대표 지시)

- 원격: `github.com/Assen-Entertainment/assen-platform` (private)
- **main = prod.** 직접 push 금지(부트스트랩 제외). `dev → main` 머지는 릴리즈 게이트 — 인간 승인 필수(프로덕션 #30).
- **dev = 통합 브랜치** (dev 서버 배포 대상). feature 브랜치만 머지 가능.
- **feature/ass-<이슈번호>-<slug>** = 작업 단위, Linear 이슈와 1:1. PR 제목·본문에 이슈 ID.
- 머지 조건(feature→dev): CI 게이트(lint+typecheck+test+build) green · 검증 계약 증거 첨부 · 작성자≠검토자 리뷰 통과.
- **코드 주석·타입 계약:** Dart public API는 `///` doc comment 의무, Python은 타입 힌트 + docstring 의무. 주석은 *why*를 설명한다(Clean Code) — 코드가 말하는 *what*의 중복 금지. 의미 있는 이름·작은 함수·단일 책임.

## 작업 방식

- 계획 → 작은 diff → 검증, 루프를 빠르게. 같은 문제 2회 교정 실패 시 컨텍스트 버리고 재시작.
- 태스크는 Linear 프로젝트 "Assen Platform"(팀 ASS)에서 추적한다. 작업 시작 시 이슈 상태 갱신, PR에 이슈 ID 연결.
- AI 실수 발견 시 `Company-OS/07_LLM/LLM_Mistake_Ledger.md`에 기록 후 이 파일 또는 hook 강화로 환류.
- 규칙 추가는 실제 사건 기반으로만 — 이 파일은 200줄 이하 유지.
