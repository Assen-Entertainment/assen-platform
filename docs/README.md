# docs/ 인덱스

25개 이상의 문서가 흩어져 있어 발견성 확보를 위해 만든 카테고리별 목록이다. **정본은 항상
코드 또는 Company-OS SDLC**이며, 여기 문서 대부분은 그 참조용 투영/레퍼런스다 — 각 항목의
정본 포인터를 따라간다. 신규 합류자는 이 문서보다 [`onboarding.md`](onboarding.md)를 먼저 읽는다.

status 표기: **current**(현행 유지) · **superseded**(대체됨, 참고용 보존) · **reference**
(스크립트/절차 레퍼런스, 설계 정본은 별도) · **research**(근거 조사, 비-규범).

## 아키텍처 / ADR

| 문서 | status | 내용 |
|---|---|---|
| [`CONSTRAINTS.md`](CONSTRAINTS.md) | current* | 개발 제약사항 41개(기준 문서). *일부 항목(#11~13, Flutter-web 전제)은 2026-06-30 방향 전환으로 재검토 대상 — 문서 상단 주 참조 |
| [`adr/0001-backend-django.md`](adr/0001-backend-django.md) | current | 백엔드 = Django 5.2 LTS + Django Ninja |
| [`adr/0002-auth-strategy.md`](adr/0002-auth-strategy.md) | current | 인증 = opaque 토큰 + refresh 회전 |
| [`adr/0003-hosting-aws.md`](adr/0003-hosting-aws.md) | current* | 호스팅 = AWS Seoul + ECS Fargate. *범위가 백엔드(API·Celery)로 좁혀짐 — 웹 호스팅은 E10 게이트 재검토 중 |
| [`adr/0004-token-codegen.md`](adr/0004-token-codegen.md) | current* | 디자인 토큰 코드젠 = Style Dictionary. *단일 소스가 tokens.json→tokens.v2.json으로 교체 중(과도기) |
| [`adr/0005-web-react-next.md`](adr/0005-web-react-next.md) | current | 웹 = React + Next.js(Flutter Web 폐기) — 2026-07-10 신설, Company-OS ADR-09 리포-로컬 앵커 |
| [`adr/0006-toolchain-windows-uv.md`](adr/0006-toolchain-windows-uv.md) | current | 툴체인 = 순수 Windows + uv(WSL 제거) — 2026-07-10 신설, Company-OS ADR-10 리포-로컬 앵커 |
| [`backend/erd.md`](backend/erd.md) | reference | 신방향 도메인 ERD(참조용 투영) — 정본은 `server/apps/*/models.py` |

## API

| 문서 | status | 내용 |
|---|---|---|
| [`api/README.md`](api/README.md) | current | 규약 인덱스(페이지네이션·에러 taxonomy·인증) + 정본 포인터. 엔드포인트별 상세는 `/api/docs`(Swagger) |
| `api/reference.html` | reference | 정적 Redoc 문서(수동 갱신, `openapi.json` 기준) |

## 배포 / 운영

| 문서 | status | 내용 |
|---|---|---|
| [`deployment.md`](deployment.md) | reference | 로컬/dev 빌드·production ECS 배포 스크립트 사용법. 설계 정본은 Company-OS SDLC 11 |
| [`ops/production-readiness-2026-07-09.md`](ops/production-readiness-2026-07-09.md) | current | 프로덕션 준비 고도화 종합 로드맵(내부 열람용, ASS-261~283) |

## 모바일

| 문서 | status | 내용 |
|---|---|---|
| [`mobile-frontend-plan.md`](mobile-frontend-plan.md) | current* | 모바일(Flutter) 업그레이드 계획(2026-07-03 작성). *§1 툴체인 게이트는 R7에서 해소, M5(13화면)까지 실배선·dev 머지 완료 — 문서 상단 갱신 주 참조 |

## 디자인

> `tokens.md`·`handoff.md`는 이미 status에 superseded가 명시된 모범 사례 — 아래 목록은
> 현행/대체 여부를 그대로 옮긴 것이며 내용은 건드리지 않는다.

| 문서 | status | 내용 |
|---|---|---|
| [`design/design-system-fanding-redesign-2026-06-26.md`](design/design-system-fanding-redesign-2026-06-26.md) | current | 디자인 시스템 전면 재설계 스펙(Fanding 기반, tokens.v2 근간) |
| [`design/ds-spec-addendum-2026-06-28.md`](design/ds-spec-addendum-2026-06-28.md) | current | DS 스펙 부록 — 모션·elevation·타이포·브랜드·i18n·게이팅 보강 |
| [`design/a11y-qa-2026-06-27.md`](design/a11y-qa-2026-06-27.md) | current | a11y 대비 QA — 핵심 13조합 WCAG AA 통과 |
| [`design/ds-parity-audit-2026-07-06.md`](design/ds-parity-audit-2026-07-06.md) | current | 코드 ↔ Figma 컴포넌트/토큰 정합 감사(R7) |
| [`design/ds-figma-sync-2026-07-08.md`](design/ds-figma-sync-2026-07-08.md) | current | Figma 역동기 완료 — 토큰 드리프트 0, 매핑률 83.8%→98.6% |
| [`design/references.md`](design/references.md) | current | 디자인 레퍼런스 보드 |
| [`design/signature.md`](design/signature.md) | proposed | 하츠코이 시그니처 디자인 v1.1(구방향, 대표 승인 대기 — 채택 여부 미확정) |
| [`design/tokens.md`](design/tokens.md) | superseded | 디자인 토큰 스펙 v0.1(하츠코이). 정본은 `tokens.v2.json` |
| [`design/components.md`](design/components.md) | superseded | 메이드era ui_kit 컴포넌트 인벤토리. 정본은 `web/src/components/ui`(42종) |
| [`design/screens.md`](design/screens.md) | superseded | 메이드/하츠코이 화면 맵. 정본은 SDLC 08(웹)·10 §3(모바일) |
| [`design/handoff.md`](design/handoff.md) | superseded | Vite 랜딩→Flutter 앱 핸드오프 URL 계약. 신방향 웹 기준 재설계 대상(미착수) |
| `design/tokens.json` · `design/tokens.v2.json` | data | 토큰 소스 데이터(JSON) — 문서가 아닌 코드젠 입력. v2가 현행 |

## 리서치

| 문서 | status | 내용 |
|---|---|---|
| [`research/stack-and-domain-constraints.md`](research/stack-and-domain-constraints.md) | research | Flutter+Django 팬 플랫폼 기술·도메인 조사(CONSTRAINTS 근거) |
| [`research/agent-harness-discourse.md`](research/agent-harness-discourse.md) | research | AI 에이전트 하네스 담론 조사(CONSTRAINTS §4 근거) |

## docs/ 밖의 관련 문서

에이전트 하네스·스택별 셋업 가이드는 `docs/` 바깥에 있다 — 발견성을 위해 함께 적어둔다.

| 문서 | 내용 |
|---|---|
| `../AGENTS.md` | 루트 에이전트 하네스(검증 계약·GitOps·금지 영역) |
| `../server/AGENTS.md` | 백엔드(Django) 하네스 — 마이그레이션 규칙·검증 명령 |
| `../apps/AGENTS.md` | Flutter 앱 하네스 |
| `../web/ASSEN_WEB_SETUP.md` | 웹 클라이언트 셋업 가이드 |
| `../web/ASSEN_DS_VISUAL_GATE.md` | 웹 DS 시각 회귀 게이트 |
| `../e2e/README.md` | Playwright E2E 하네스(라이브 서버 대상 Claude QA 게이트) |
