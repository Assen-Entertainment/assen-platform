---
title: 디자인 시스템 전면 재설계 — Fanding 기반 (토큰 스펙 v2)
date: 2026-06-26
status: 초안 — 전면 재설계 착수(대표 2026-06-26 결정). tokens.json 반영·codegen·Figma 미러는 후속 단계
supersedes: tokens.md(v0.1 하츠코이 라이트 레트로 큐트), signature.md(하츠코이 시그니처)
note: 기존 DS(Figma mmgcToD51… 162컴포넌트)는 아카이브 보존(삭제 금지). 본 스펙이 새 단일 방향.
---

# 디자인 시스템 전면 재설계 — Fanding 기반 (토큰 스펙 v2)

근거: 대표 결정(2026-06-26, 전면 재설계) + **Fanding 실측**(chrome-devtools computed CSS, `Company-OS/60_Knowledge/Platform_Reference/`). 파이프라인 불변: **이 스펙 → `docs/design/tokens.json`(DTCG) → `packages/core_tokens` Dart(codegen) → Figma Variables 미러**. Figma는 코드 미러이므로 본 토큰/Dart 확정 후 Figma 구축.

> ⚠️ **값 정본 = `tokens.v2.json`.** 2026-06-27 fanding.kr 재계측(요소 2137개)으로 베이스라인 확정: 보조텍스트 **#9797AE**·힌트 **#B7B7CA**, onPrimaryContainer 텍스트=**인디고 #5E63F8**(라벤더 위), 보더 **#E9E9F1**, violet 틴트 **#F6EEFD**, 폰트굵기 **400/500/700**(600 미사용), radius **10** 추가. 아래 표의 일부 구값(#71717A 등)은 tokens.v2.json 우선. 기존 Figma DS(`mmgcToD51…`)는 **폐기**(아카이브 아님).

## 0. 방향 한 줄
하츠코이 레트로 큐트(크림+파스텔+모티프) → **Fanding형 클린 신뢰 레지스터**(흰/다크 + 인디고 단일 액센트 + Pretendard + 12px + 파스텔=배경/필 전용 + 콘텐츠 전면). 라이트·다크 표면별 지원(Fanding/Likey 실증).

## 1. 원칙
1. **단일 액센트 + 중성 베이스.** 멀티 파스텔 키컬러(구 DS) → 흰/다크 중성 + **인디고 단일 브랜드 액센트**. 파스텔은 카테고리 칩/아이콘 *배경·필 전용*(텍스트 금지, 동일 hue 다크 잉크).
2. **라이트·다크 양립.** 시맨틱 토큰 레이어로 light/dark 모드. **액센트(인디고)는 모드 불변**(Fanding/Likey 패턴).
3. **콘텐츠 전면.** 썸네일·아바타·카드 중심. 장식 모티프(체키프레임/스탬프/우표) 최소화 — 기능 컴포넌트는 클린 재스타일.
4. **WCAG AA.** 파스텔 텍스트 금지(전경은 잉크/액센트만). 본문 대비 ≥ 4.5:1, 다크 동일.
5. **코드가 정본.** tokens.json↔Dart↔Figma 드리프트 0 유지.

## 2. color.ref — 원시 팔레트 (Fanding 실측 기반)

### 중성 (light)
| 토큰 | 값 | 용도 |
|---|---|---|
| white | #FFFFFF | 앱 배경·카드 |
| neutral.50 | #F8F8F9 | subtle fill |
| neutral.100 | #F4F4F5 | 보조 서피스/필 (Fanding 실측) |
| neutral.200 | #E9E9F1 | hover/divider (Fanding 실측) |
| neutral.300 | #D4D4D8 | border |
| ink.900 | #191919 | 본문·제목 (Fanding bodyColor 실측) |
| ink.600 | #52525B | 보조 텍스트 |
| ink.500 | #71717A | 비활성·placeholder (Fanding/Crepe 실측) |
| ink.400 | #9797AE | 힌트(gray-purple, Fanding 실측) |

### 중성 (dark)
| 토큰 | 값 | 용도 |
|---|---|---|
| dark.bg | #141417 | 앱 배경 |
| dark.surface | #1C1C20 | 카드/서피스 |
| dark.surfaceHigh | #26262B | 보조 서피스 |
| dark.border | #34343A | border/divider |
| dark.ink | #F4F4F5 | 본문 |
| dark.inkSub | #A1A1AA | 보조 |

### 브랜드 액센트 (인디고 — 라이트/다크 불변)
| 토큰 | 값 | 용도 |
|---|---|---|
| indigo.500 | #5E63F8 | **primary 액센트** (CTA·활성·링크, Fanding 실측) |
| indigo.600 | #4B50E0 | pressed |
| indigo.100 | #EFEFFE | accentContainer/필 (Fanding 실측 라벤더) |
| indigo.ink | #2E2C8A | 라벤더 필 위 텍스트 |

### 카테고리 파스텔 (bg/fill 전용 + 동일 hue 잉크) — Fanding 실측
| hue | bg(fill) | ink(텍스트/아이콘) |
|---|---|---|
| lavender | #EFEFFE | #4338CA |
| cream | #FFF9EB | #926A14 |
| mint | #E8FEF1 | #166534 |
| sky | #E7F6FF | #1F566B |
| pink | #FFF2F2 | #9F1239 |
| zinc | #F4F4FA | #3F3F46 |

### 상태
| 토큰 | 값 |
|---|---|
| success | #22C55E |
| warning | #F59E0B |
| error | #EF4444 / bg #FFF2F2 / ink #9F1239 |

## 3. color.sys — 시맨틱 역할 (M3, light/dark 모드)

| 역할 | light | dark |
|---|---|---|
| surface | white | dark.bg |
| surfaceContainer | white | dark.surface |
| surfaceContainerHigh | neutral.100 | dark.surfaceHigh |
| onSurface | ink.900 | dark.ink |
| onSurfaceVariant | ink.500 | dark.inkSub |
| outline | neutral.200 | dark.border |
| **primary** | **indigo.500** | **indigo.500** (불변) |
| onPrimary | white | white |
| primaryContainer | indigo.100 | #2A2A52 |
| onPrimaryContainer | indigo.ink | #C7C9FF |
| error | error | error |
| surfaceTint | 사용 안 함 | 사용 안 함 |

- 구 DS의 `rose #C2486B`/`cream`/`strawberry` 등 키컬러 → **deprecated**(아카이브). primary는 인디고로 단일화.

## 4. typography

폰트: **Pretendard (Variable)** 단일(라틴+한글). 보조 라틴 숫자 필요 시 동일. 구 DS의 카페24써라운드/갈무리/Jua → **deprecated**.

| 슬롯 | 크기/행간/굵기 | 용도 |
|---|---|---|
| display.l | 28/36/700 | 화면 히어로 |
| display.m | 24/32/700 | 섹션 헤드 |
| headline | 20/28/700 | 카드/섹션 타이틀 (Fanding 실측) |
| title.l | 18/26/600 | 리스트 타이틀 |
| body.l | 17/26/400 | 본문 강조 (Fanding 실측) |
| body.m | 15/23/400 | 기본 본문 (한글 행간 1.5+) |
| body.s | 13/20/400 | 보조 |
| label | 14/20/600 | 버튼/탭/칩 |
| caption | 12/16/500 | 하단탭·메타 |

> ⚠️ **Figma 폰트 제약:** 현 Figma 환경에 **Pretendard 미설치(Jua만)**. Figma 미러 구축 전 Pretendard를 Figma org/desktop에 추가하거나(권장) 대체 폰트 결정 필요. **Dart/코드는 Pretendard 사용 가능**(앱 번들 임베드) — 코드와 Figma의 폰트 불일치 주의.

## 5. radius / spacing / elevation / motion
- **radius**: xs 4 / sm 8 / **md 12(기본, Fanding 실측)** / lg 16 / xl 24 / full 999(pill — Crepe/b.stage 다용). 카드·배너 12, 칩·버튼 pill 또는 8.
- **spacing**(4dp): 4·8·12·16·20·24·32·40·48·64. 화면 마진 16~20, 카드 내부 16.
- **elevation**: 보더 우선(Fanding). level0=보더만 / level1=카드 y2 blur8 8% / level2=시트 y8 blur24 12%. 다크는 surfaceHigh로 위계.
- **motion**: short 120 / standard 200 / medium 300. easing standard cubic-bezier(0.2,0,0,1). 과한 연출 지양(클린).

## 6. 컴포넌트 방향 (클린 재스타일 — 기존 162개 → 신규 매핑)

| 그룹 | 컴포넌트 | 재설계 방향 |
|---|---|---|
| 내비 | TabBar(하단 5탭), AppBar, SegmentedTabs, UnderlineTabs | 라벤더 활성 인디고, 라이트/다크 |
| 액션 | Button(primary=indigo filled/pill, secondary=outline, ghost), BottomCTA | 단일 액센트 |
| 입력 | TextField/SearchField(neutral.100 필), Checkbox/Radio/Switch(indigo) | Fanding형 필 인풋 |
| 컨테이너 | Card(12px, 보더 우선), BottomSheet, Dialog, ListItem(chevron) | 흰/다크 |
| 콘텐츠 | Avatar(원형), BannerCard(히어로 캐러셀), ThumbnailCard(크리에이터/상품), CategoryChip(파스텔 아이콘) | 콘텐츠 전면 |
| 도메인(신규/재스타일) | **CreatorHome**(아바타+탭: 포스트/멤버십/스토어), **MembershipTierCard**, **ProductCard/GroupBuyCard**, **CheckoutSheet**(약관4종·본인인증·VAT분리 — 아키텍처 §4·§10), **GiftSheet**(하트, Likey형), **CastNote/FanLetter**(검수형) | 거래/멤버십/선물/소통 |
| 수집(재스타일) | ChekiFrame, StampCard, MembershipCard(회원증) | 모티프 최소화·클린(레트로 제거) |
| 피드백/운영 | Toast/EmptyState/Skeleton/StatusBadge, 운영자 DataTable/검수큐 | — |

## 7. 마이그레이션 / 다음 단계
1. **본 스펙 검토** → tokens.json 신규 작성(light/dark 모드, DTCG) → `melos run codegen`(Dart) → 골든 회귀.
2. **Figma 미러**(신규 파일): figma-use 스킬 → Variables(color light/dark·spacing·radius)·텍스트스타일·핵심 컴포넌트. **폰트 결정 선행**(Pretendard 추가 or 대체).
3. 기존 DS(mmgcToD51…) 아카이브 표기(삭제 금지).
4. 거래/멤버십/선물 신규 도메인 컴포넌트는 아키텍처(`Company-OS/03_Engineering/하츠코이_플랫폼_시스템아키텍처`)의 화면·flag와 정합.

## 8. 인간 게이트
- 액센트 확정(인디고 #5E63F8 채택 vs 대표 다크-모노 의향 반영) = 대표.
- 라이트 우세 vs 다크 우세(표면별 기본 모드) = 대표(Likey식 혼용 가능).
- Figma 폰트(Pretendard 설치 가능 여부) = 디자인/운영.
- 수집 표면 하츠코이 모티프 완전 제거 vs 일부 기능 유지 = 대표(전면 재설계 = 제거 기본, 단 체키/회원증 기능성 확인).

## 9. 전략 정정 반영 — 순수 범용 플랫폼 (메이드 스코프 완전 제거, 2026-06-27 2차)

대표 결정(2026-06-27 2차 "완전 제거", [[전략_방향_범용크리에이터플랫폼_2026-06-27]]): 제품 = **순수 범용 크리에이터 플랫폼**. 메이드 테마·프리셋·레지스터 **전부 제거**.

- **단일 클린/범용 레지스터(인디고).** 메이드/큐트 레지스터·`color.ref.hatsukoi` **삭제됨**(`tokens.v2.json`에서 제거 완료). 표면 종류로 레지스터를 가르지 않음 — 플랫폼 chrome 전부 클린/인디고.
- **개성 = 크리에이터별 프로필 테마**(커버·액센트, 메이트유·Likey식) = 크리에이터 자율 표현 레이어. DS엔 메이드 프리셋 없음; 향후 일반 `theme.{creator}` 사용자 액센트(런타임)만.
- **무효 처리(SUPERSEDED):** 본 문서 §0·§1·§6의 "하츠코이 레트로 큐트/수집 표면 모티프", §8 게이트의 "수집 표면 모티프 유지", 기획보고서 §7 "표면별 레지스터 맵(수집 vs 상거래)" = **무효**. ChekiFrame/StampCard/MembershipCard 등 메이드·수집 컴포넌트(§6)는 스코프 아웃.
- **유지 기능(범용, 메이드 무관):** 크리에이터홈 = 포스트/멤버십/스토어/**퀘스트(검수형)** 탭(메이트유식), GiftSheet = 후원/가상선물(모델 후보, IAP=G4 게이트), 프라이빗 피드(멤버십+단건). 출근표/방문/MSFC = **스코프 아웃**.
- 게이트: 가격/정산/약관/IAP/콜드스타트 시드 = 대표·법무.
