---
title: DS Figma 역동기 · 전체 정합성 합치 (R7 감사 §6 실행)
date: 2026-07-08
status: 완료 — Tier1/2/4 반영·검증 완료, Tier3 코드-only 11 등재·검증 완료 (2026-07-08)
supersedes-actions-in: "[[ds-parity-audit-2026-07-06.md]] §6"
related:
  - "[[ds-parity-audit-2026-07-06.md]]"
  - "[[tokens.v2.json]]"
  - "[[ASSEN_DS_VISUAL_GATE.md]]"
figma:
  fileKey: Snd7m8KauF51QBZL5LWuGu
  page: "02 Components (5:3)"
  auth: owsqix (pro, expert seat) — whoami 확인됨 2026-07-08
  editor: design
---

# DS Figma 역동기 · 정합성 합치 (2026-07-08)

## 0. 배경 · 근거

R7 감사(`ds-parity-audit-2026-07-06.md`)는 코드↔Figma 매핑 83.8%와 미반영 백로그(토큰 드리프트 1·의도적 편차 4·코드-only 11·Figma-only 6)를 산출하고, **모든 Figma 쓰기를 "브랜드 방향 E9 확정 후행"으로 동결**했다. 2026-07-08 대표(건용) 지시 "미반영 백로그 Figma 반영 + 문서와 전체 Figma 정합성 점검/합치"로 동결 해제, 아래를 실행.

**SSOT 규율 불변**: 정본 = `tokens.v2.json`(토큰) + 코드 컴포넌트. Figma는 미러 → 코드값을 Figma에 반영(역동기)한다. 쓰기 전 라이브 변수/노드값을 직접 재감사해 문서 주장을 재확인한 뒤에만 변경.

라이브 재감사(2026-07-08, `use_figma` read-only)로 확인한 파일 구조:
- 페이지 6개: `00 Cover`, `01 Foundations(0:1)`, `02 Components(5:3)`, `03 Templates(5:4)`, `04 Screens(87:2)`, `05 Web(147:3)`
- 변수 컬렉션: Primitives(40·mode Value) · Semantic(22·Light/Dark) · Spacing(11) · Radius(7) · Creator(1·Teal/Coral) · Chart(12)

---

## 1. Tier 1 — 토큰 드리프트 해소 ✅ (완료·검증)

라이브 재감사 결과, 문서가 지목한 warning 드리프트의 **실 원인은 프리미티브 1개**로 좁혀짐(그 외 warning 계열은 이미 정합):

| 변수 | 반영 전 | 반영 후 | 근거 |
|---|---|---|---|
| `ref/amber/main` (Primitives `VariableID:1:37`, mode Value `1:0`) | `#ce8509` | **`#b8740a`** | tokens.v2 `color.ref.amber.main` = `#B8740A` (WCAG 1.4.11: white 3.79 / cream.bg 3.61) |
| `sys/warning` Light (`VariableID:2:20`, mode `2:0`) | →alias amber.main(구값) | **`#b8740a`**(alias 자동정정) | `sys.warning = {amber.main}` alias 구조 정합 |

이미 정합이라 **미변경**(라이브 확인): `sys/warning` Dark `#f5b53d`(=tokens `sysDark.warning #F5B53D`), `sys/warningContainer` L/D `#fff9eb`/`#3a2e12`, `sys/onWarningContainer` L/D `#926a14`/`#f5d98a`.

→ **토큰 드리프트 0건**. 영향: Badge warning-container·경고 표면.

---

## 2. Tier 2 — 의도적 편차 4건 Figma 반영 ✅ (완료·시각검증)

감사 §5의 "코드 선행" 편차 4건을 실제 노드에 반영(라이브 스크린샷 검증). 파괴적: 기존 노드 속성 변경(#1·#2·#4) + 신규 클론 1개(#3, 원본·인스턴스 무손상).

| # | 컴포넌트 | 노드 | 반영 내용 | 검증 |
|---|---|---|---|---|
| 1 | CreatorThumbCard | 커버 `31:4` | SOLID 회색 → **`gradient/brand`** Paint Style(`S:ab540ae7…`) 바인딩 | ✅ 인디고→바이올렛 그라데이션 렌더 확인 |
| 2 | EmptyState | 서클 `39:4` | SOLID 회색 → **`sys/primaryContainer`**(`VariableID:2:12`) 변수 바인딩 | ✅ 라벤더 틴트 확인 |
| 4 | PriceLabel | `51:8`·`51:9` | 원가 `₩12,000` → **STRIKETHROUGH**, 할인율 `18%` → **`sys/error`**(`VariableID:2:15`) 바인딩 | ✅ 취소선+적색 확인 |
| 3 | MembershipTierCard | 신규 `297:28`(바 `297:49`) | 원본(`19:3`) 클론 → **`MembershipTierCard / Featured`**: flush **`gradient/brand`** 상단 바 + "프리미엄 멤버십" 라벨 | ✅ 상단 바+라벨 확인 |

> #3만 비파괴 별도 컴포넌트로 처리(원본 `19:3`을 variant set으로 변환하면 기존 인스턴스가 파손될 수 있어, 클론 신설로 featured 트리트먼트를 등재). 향후 정식 variant 통합은 브랜드 확정 후 선택.

→ 감사 §5 편차 **4/4 동기 완료**(이전 "완전동기 0").

---

## 3. Tier 3 — 코드-only 11건 Figma 등재 ✅ (완료·검증)

감사 §3-1의 코드-only 11건(gate-note 제외)을 `02 Components` 페이지 신규 섹션 **`06 Code-Sync (R7 · 2026-07-08)`**(Section `299:28`, board `299:29`, x=5130/y=6285 — 기존 최하단 y≈6085 아래)에 additive 등재(designer/opus). 기존 6개 섹션(Atoms/Molecules/Organisms/Policy/Commerce/MembershipTierCard) 및 전 노드 **무손상**(생성만, 변경 0). 라이브 검증: 섹션 내 COMPONENT 11개 실측 + 보드 스크린샷 확인.

| # | 컴포넌트 | 노드 | 코드 경로 |
|---|---|---|---|
| 1 | Accordion | `301:28` | web/src/components/ui/accordion.tsx |
| 2 | FileUpload | `300:41` | web/src/components/ui/file-upload.tsx |
| 3 | DatePicker | `308:28` | web/src/components/ui/date-picker.tsx (Calendar 인스턴스 임베드) |
| 4 | Calendar | `307:28` | web/src/components/ui/calendar.tsx (2026-07, today=8, selected=15) |
| 5 | Breadcrumb | `300:33` | web/src/components/ui/breadcrumb.tsx |
| 6 | MediaViewer | `306:28` | web/src/components/ui/media-viewer.tsx |
| 7 | SuccessCheck | `300:28` | web/src/components/ui/success-check.tsx |
| 8 | Shelf | `305:28` | web/src/components/ui/shelf.tsx |
| 9 | Sidebar | `303:28` | web/src/components/ui/sidebar.tsx |
| 10 | TopBar | `302:28` | web/src/components/ui/topbar.tsx |
| 11 | RightRail | `304:28` | web/src/components/ui/right-rail.tsx |
| 12 | LoadMore | `313:126` (component set: `313:116` Default / `313:119` Loading) | web/src/components/ui/load-more.tsx |

**토큰 규율**: 전 surface/text/container/border fill을 `sys/*` 변수 바인딩, 그라데이션 아트는 `gradient/brand` Paint Style, 타이포 Noto Sans KR + DS 타입램프(title-l/m·label·body-m/s·caption), radius 6/8/12/full. 각 컴포넌트 `description`=코드 경로.

**★델타 동기화 (2026-07-12)**: 07-08 이후 신규 DS 컴포넌트 **LoadMore**(07-10 추가, `web/src/components/ui/load-more.tsx`)를 Code-Sync 섹션에 additive 등재(위 12행). **첫 COMPONENT_SET 엔트리**(Default/Loading 변형 — 스피너·dimmed 로딩 버튼). 기존 11개 엔트리+전 섹션 무손상(라이브 재감사·스크린샷 검증). ★free-grant UI(ASS-297)는 앱 뷰(checkout/membership/studio)이지 DS 컴포넌트가 아니라 Figma DS 델타 없음. 브랜드색 #5A4DF0는 07-08 미러 유지. → **DS 대상 매핑 74/74 = 100%**.

**알려진 편차 1건(드리프트 로그 등재)**: MediaViewer Figma에 좌/우 nav 화살표 존재하나 현행 `media-viewer.tsx`는 단일 미디어(scrim+미디어+close, 화살표 없음). → 후속: 코드에 화살표 추가 또는 Figma 화살표 제거로 정합(경미, 표준 라이트박스 크롬). 오버레이 크롬 색(black/85·white/10)은 시맨틱 토큰 부재로 코드 리터럴값 미러(허용).

---

## 4. Tier 4 — Figma-only 6건 정합성 판정 ✅ (문서 판정)

감사 §3-2(가)의 "디자인만 있고 코드 없는" 실갭. **코드 6개 신규 구현은 이 합치의 범위 밖**(별도 로드맵) → 정합성 판정만 기록. 라벨=디자인 선행(design-ahead), SSOT는 여전히 코드이므로 "미구현"은 드리프트가 아니라 **로드맵 후보**로 확정.

| Figma-only | 노드 | 판정 | 근거 |
|---|---|---|---|
| ProgressRing | `52:5` | 로드맵 후보(P2) | 원형 진행 표시 — 코드 미사용. 도입 시 신규 |
| Rating | `54:17` | 로드맵 후보(P2) | 별점 — 리뷰 기능 도입 시 |
| Slider | `55:3` | 로드맵 후보(P3) | 범위 입력 — 현 폼에 미사용 |
| CountdownTimer | `59:9` | 로드맵 후보(P2) | 카운트다운 — 드롭/이벤트 기능 도입 시 |
| ScrollProgressBar | `64:3` | 로드맵 후보(P3) | 스크롤 진행 — 롱폼 콘텐츠 도입 시 |
| QuestCard | `27:13` | 보류(기능 미정) | 퀘스트 도메인 미구현 |

참고(감사 §3-2 재확인) — 아래 4건은 실갭 아님(기존 코드로 대체/조합, 등재 불요): ProductCard→MonetizableItem, FilterChipRow→Chip 조합, CheckoutSheet→앱 라우트 조합, AgeGate→locked-overlay+게이팅.

→ Figma-only 실갭 **판정 완료**: 신규 구현 대상 아님(로드맵 편입 판단만 남음). Figma 측 정리(삭제/리네임) **불요**.

---

## 5. 갱신된 정합성 수치

- 토큰 드리프트: 1 → **0**
- 의도적 편차 동기: 0/4 → **4/4**
- 코드-only 미등재: 12 → **1**(gate-note, 개발전용 의도적 제외만 잔존)
- 코드↔Figma 매핑률(감사 기준 74 컴포넌트): 62/74(83.8%) → **73/74 = 98.6%**. DS 등재대상(gate-note 제외 73)만 보면 **73/73 = 100%**.
- Figma-only 실갭: 판정 완료(로드맵 분류, 신규 구현 대상 아님)

---

## 6. 잔여 · 후속

- ✅ **Tier 3 반영 완료**: 노드 ID §3 표 등재, 매핑률 98.6%(DS대상 100%) 재산출.
- **MediaViewer 화살표 편차**(§3): 코드↔Figma 정합 후속 1건(경미).
- **문서 동기**: 본 반영 후 `ASSEN_DS_VISUAL_GATE.md §5`(편차 상태 → 동기 완료)·`ds-parity-audit §6`(액션 → 실행됨) 헤더 갱신.
- **브랜드 확정 후행(불변)**: indigo `#5A4DF0` 대표 최종 사인, gradient.brand 계열 브랜드 방향 재확인 시 재점검(현 반영은 코드 현행값 미러).
- **정식 variant 통합**(선택): MembershipTierCard Default/Featured를 variant set으로 통합(기존 인스턴스 마이그레이션 동반).
