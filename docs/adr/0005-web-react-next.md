# ADR-0005: 웹 클라이언트 스택 — React + Next.js (Flutter Web 폐기)

- 날짜: 2026-06-29 (Company-OS 확정) · 2026-06-30 플랫폼 방향 전환 공표로 시행
- 상태: Accepted
- 결정자: 대표 (Geon Yong Kim)
- Company-OS 원본: `Company-OS/02_Product/SDLC/07_의사결정기록_ADR_및_회고.md` ADR-09 ·
  구체화 `SDLC/08_웹클라이언트_React구현_및_백로그재편_2026-06-30.md` §5
- 리포 내 "ADR-09" 인용 정정: 본 리포(`docs/adr/`)는 0001부터 시작하는 독립 번호열이라
  Company-OS의 ADR-09와 번호가 다르다. 이 문서가 그 결정의 리포-로컬 앵커다 — README.md·
  `docs/adr/0003-hosting-aws.md`·`web/ASSEN_WEB_SETUP.md`·`web/ASSEN_DS_VISUAL_GATE.md`의
  "ADR-09" 인용은 본 문서(0005)를 가리킨다.

## 맥락

기존 웹UI 기획(`웹UI_기획_2026-06-28`, Company-OS)은 Flutter Web 단일 전제였다. 그러나
웹 우선 출시 + 통판/디스커버리 표면은 SEO·SSR·초기 로딩이 핵심 요구인데, `docs/CONSTRAINTS.md`
#11~13이 이미 기록했듯 Flutter web은 검색엔진 인덱싱 비적합(공식 FAQ)과 1~2MB 초기 페이로드
문제를 안고 있었다. 2026-06-29 레퍼런스 전수조사(`docs/research/stack-and-domain-constraints.md`)
결과 동종 서브컬쳐/크리에이터 플랫폼이 **전부 웹 네이티브**였다: Fanding=Vue, Likey=Next.js/React,
Patreon=Next.js, madeyou=imweb — Flutter Web 사용 사례 0건.

## 결정

**웹 = React + Next.js(App Router) + TypeScript + Tailwind v4 + Radix**(SSR/SEO 확보),
**모바일 = Flutter 유지**(기존 `packages/ui_kit`·`packages/features`(auth)·앱셸 자산 보존).
플랫폼 간 공유는 코드가 아니라 **디자인 토큰**(`tokens.v2.json` → 웹은 CSS 변수/TS,
모바일은 `.gen.dart`)과 Figma DS 규약 수준에서만 이뤄진다 — 컴포넌트 구현은 플랫폼별로 별도 작성.

- 웹 스캐폴드는 `web/`(Next 15 + React 19)에 신설. 기존 `apps/fan_app`·`apps/operator_app`의
  Flutter-web 경로는 M10 아카이브 대상(구방향 잔재)이며, 모바일 전용 자산(`apps/assen_mobile`)만
  Flutter 레인으로 존속한다.
- 스타일링은 Tailwind v4로 확정(CSS Modules는 검토했으나 미채택). styled-components는
  React Server Component 마찰·런타임 비용·메인테넌스 모드 논의로 배제.
- API 계약은 `openapi.json`(서버 생성) → `npm run gen:types`로 웹 타입 역생성 — ADR-0001의
  Django Ninja 스키마 우선 원칙을 웹 소비자 쪽에서 그대로 승계.

## 대안 검토

- **Flutter Web 단일 스택(기존 전제)**: SEO 인덱싱 공식 비적합, 초기 페이로드 과다, 한국어 IME
  약점(CONSTRAINTS #13)까지 겹쳐 웹 우선 출시 요구와 상충. 폐기.
- **React Native for Web 등 코드 공유 접근**: 모바일이 이미 Flutter로 확정돼 있어 RN 계열의
  "모바일과 코드 공유" 이점이 무의미해진다. 채택 안 함.
- **styled-components**: RSC 비호환·번들 비용·유지보수 정체로 배제, Tailwind v4로 대체.

## 결과

- `web/`이 신방향 웹 앱의 유일한 표면 — 라우트·DS 컴포넌트·React Query·B-API 연동은
  ASSEN_WEB_SETUP.md·`docs/deployment.md` "Web (Next.js — 신방향)" 절 기준.
- `docs/adr/0003-hosting-aws.md`(호스팅 ADR)의 범위가 백엔드(API·Celery)로 좁혀지고, 웹 호스팅은
  Vercel vs ECS 재검토(E10 게이트, SDLC 08 §4 / SDLC 11 §3)로 이관됐다.
- `docs/design/handoff.md`(랜딩→Flutter 핸드오프 URL 계약)는 이 결정으로 superseded 처리됨 —
  신방향 핸드오프는 `web/` 기준 재설계 대상(미착수).
- 리스크: 웹·모바일 두 플랫폼이 컴포넌트 코드를 공유하지 않으므로 네이밍(`ds-parity-audit`)과
  토큰 드리프트를 별도 감사 루프로 관리해야 한다(2026-07-08 역동기로 드리프트 0 확인 완료).
