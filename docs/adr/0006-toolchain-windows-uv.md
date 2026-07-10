# ADR-0006: 개발 툴체인 — 순수 Windows + uv (WSL 제거)

- 날짜: 2026-06-30(Company-OS 결정 승계) · 2026-07-01 WSL 제거로 전면 시행
- 상태: Accepted
- 결정자: 대표 (Geon Yong Kim)
- Company-OS 원본: `Company-OS/02_Product/SDLC/07_의사결정기록_ADR_및_회고.md` ADR-10 ·
  구체화 `SDLC/08_웹클라이언트_React구현_및_백로그재편_2026-06-30.md` §5
- 리포 내 "ADR-10" 인용 정정: 본 리포(`docs/adr/`)의 독립 번호열에서 이 문서가 그 결정의
  리포-로컬 앵커다 — README.md·`web/ASSEN_WEB_SETUP.md`·`web/ASSEN_DS_VISUAL_GATE.md`의
  "ADR-10" 인용은 본 문서(0006)를 가리킨다.

## 맥락

기존 빌드/검증 절차 다수는 "build=WSL" 전제로 작성돼 있었다(웹 `next build`, Django
`pytest`/`uv run`, e2e Playwright 시드 절차 등). 2026-07-01, 디스크 사유로 WSL을 제거하고
전 툴체인을 순수 Windows로 전환했다. 웹은 Windows npm으로 `next build`가 즉시 성공했으나,
Python 쪽은 `uv`가 POSIX 셸 전제(PATH 배선·`uv run`의 비대화형 셸 가정)로 설계돼 있어
Windows 네이티브에서 그대로 쓸 수 없었다.

## 결정

**전 스택을 순수 Windows 툴체인으로 확정한다.** pnpm·WSL 재구축은 불요.

- **Python/Django**: `uv`는 의존성 관리 도구로 유지하되, Windows에서는 **체크아웃된 venv
  `server/.venv-win`을 직접 호출**한다(`.venv-win\Scripts\python.exe -m pytest` 등) —
  `uv run`이 비대화형 환경에서 PATH를 배선하지 못하는 문제를 우회. 의존성 동기화는
  `UV_PROJECT_ENVIRONMENT=.venv-win` 환경변수로 `uv sync`의 타깃을 고정하고, 개별 패키지
  상시 추가는 `uv pip install --python .venv-win/Scripts/python.exe <pkg>`로 수행한다.
- **Node/웹**: Windows npm(node 24 / npm 11) — pnpm 불필요, `web/`·`e2e/`·`landing/` 전부
  `npm install`/`npm run *`로 통일.
- **Flutter/모바일**: Windows 네이티브 SDK 설치(`C:\Users\daisy\flutter`, R7) — WSL 경유
  없이 `dart format`/`analyze`/`test`/`flutter build` 로컬 실행.
- **git**: Windows 네이티브 HTTPS(origin은 GitHub 그대로).

## 대안 검토

- **WSL 유지·재구축**: 디스크 용량 사유로 최초 제거를 결정했고, 재구축은 그 사유를 되돌리지
  못해 비권장(구방향 `docs/mobile-frontend-plan.md` §1(c)에서도 동일 결론).
- **pnpm 도입**: Windows npm만으로 전 빌드가 성공해 추가 도구 도입 실익 없음. 채택 안 함.

## 결과

- `server/AGENTS.md`·`AGENTS.md`(루트)의 검증 계약이 `.venv-win` 직접 호출 경로로 갱신됨.
- 신규 개발자 온보딩 절차는 `docs/onboarding.md`(신규)가 정본 — Day-1에 `.venv-win`·npm·
  Flutter·e2e 순서로 셋업한다.
- **함정(빈발)**: 실행 중인 로컬 서버가 `.pyd`(컴파일된 확장 모듈) 파일을 점유한 상태에서
  `uv sync`를 돌리면 파일 잠금으로 실패한다 — 서버 프로세스를 정지한 뒤 재시도한다.
- `e2e/README.md`의 시드 절차도 이 결정에 맞춰 재작성됨 — PowerShell은 `<` stdin 리다이렉트를
  지원하지 않아 `manage.py shell < script.py`가 아니라
  `manage.py shell -c "exec(open('script.py', encoding='utf-8').read())"` 패턴을 쓴다.
