---
title: DS 스펙 부록 — 어드버서리얼 리뷰 must_fix 대응 (모션·elevation·타이포·브랜드·i18n·게이팅)
date: 2026-06-28
status: 코드 준비용 스펙. 리뷰(2026-06-28, major_gaps 5.25)의 DS·심미 갭 보강. ★=제품/법무 결정 필요.
related:
  - "[[tokens.v2.json]]"
  - "[[ultragoal_완료보고_전체플랫폼Figma_2026-06-27]]"
  - "[[design-system-fanding-redesign-2026-06-26]]"
---

# DS 스펙 부록 (리뷰 보강)

리뷰가 지적한 "월드클래스/코드준비"의 미충족 스펙을 명문화. **2026-06-28 재리뷰 반영: 정적 토큰(`motion.easing.*` 4곡선·`motion.spring`·`elevation.level0~4`·`focus.ring`·`state.disabledOpacity`·`gradient.brand`·`dimension.safeArea/breakpoint`·`typography.scale.displayXL` 32)을 `tokens.v2.json`에 실제 인코딩 완료**(이전 "prose-only vapor" 정정). **단 `creatorAccent`는 정적 토큰 아님 — 임의 입력색의 WCAG/APCA 자동 대비보정은 Dart 런타임 유틸로 구현**(§4b, codegen 미생성).

## 1. 모션 (단일 easing → 다중 곡선 + reduced-motion)
| 토큰 | cubic-bezier | 용도 |
|---|---|---|
| `motion.easing.standard` | (0.2, 0, 0, 1) | 기본 전환 |
| `motion.easing.decelerate` (enter) | (0, 0, 0, 1) | 진입(시트·다이얼로그·페이지 push) |
| `motion.easing.accelerate` (exit) | (0.3, 0, 1, 1) | 이탈(pop·dismiss) |
| `motion.easing.emphasized` | (0.2, 0, 0, 1)·spring | 강조(시트 확장·딜라이트) |
| `motion.spring.sheet` | mass1·stiffness220·damping26 | BottomSheet drag/settle |
| duration | short 120 / standard 200 / medium 300 / emphasized 400 | — |

**컴포넌트 매핑:** Sheet=medium+decelerate(enter)/short+accelerate(exit)·drag-to-dismiss(spring); Dialog/Modal=standard+decelerate+scale .96→1; Toast/Snackbar=short; 페이지 push=standard+decelerate(L→R); 좋아요/선물=spring pop; 리스트=stagger 24ms; pull-to-refresh=spring.
**reduced-motion(WCAG 2.3.3):** `prefers-reduced-motion` 시 모든 이동/스케일/패럴럭스 제거 → opacity 페이드(100ms)만. shimmer→정적 skeleton.

## 2. Elevation (2단 → 5단 z-스택)
| 토큰 | 용도 | 라이트 | 다크(surface 톤+border) |
|---|---|---|---|
| `elevation.0` | 평면/카드 보더 | border outline | border dark.border |
| `elevation.1` | 카드/PostCard | y1 b3 0.06 | surfaceHigh, border |
| `elevation.2` | popover·Menu·드롭다운 | y4 b12 0.10 | surface+1, border |
| `elevation.3` | FAB·BottomCTA·Snackbar | y6 b16 0.12 | +brighter border |
| `elevation.4` | Sheet·Dialog·Modal | y12 b32 0.16 | scrim + surface+2 |
다크는 그림자 대신 surface 단계 + border로 깊이 표현(원칙 유지).

## 3. 타이포 위계 정리 (15~20px 6슬롯 과밀 해소)
- **클러스터 정리:** `body.l 17` 역할을 "긴 본문"으로 한정, `title.m 16`은 "리스트/카드 타이틀"로 유지하되 **weight 점프 강제**(title=700, body=400) — 1px 차가 아닌 weight로 변별.
- **히어로 상향:** `display.l 28 → 32`(모바일 히어로 임팩트), `display.m 24` 유지. (현 화면은 DisplayM 24 사용 중 → 히어로 화면만 32 적용)
- **weight 정리:** 400/500/700 유지, **600 잔재 제거**(마크다운 스펙 표의 title.l/label 600 표기 → 정본대로 700/500). 보조 위계는 색(ink.500)·letter-spacing(-0.01em 제목)으로.

### 3-1. ★폰트 일원화 확정 (2026-06-28)
재리뷰가 지적한 3중 드리프트(Figma=Noto Sans KR / tokens=Pretendard / 생성코드=Cafe24 Ssurround) 해소 결정:
- **Canonical = Pretendard Variable (전 제품 단일).** `tokens.v2.json typography.fontFamily.display/body` = Pretendard ✅(이미 일치). 출고 타이포의 단일 진실.
- **코드:** `typography.gen.dart`의 Cafe24 Ssurround는 **구 tokens.json에서 생성된 잔재** → G012 codegen이 tokens.v2를 읽으면 자동 제거·Pretendard로 통일. 라이선스 **Pretendard 서브셋을 앱/`ui_kit`에 번들 + pubspec `fonts:` 선언**(코드레인 §5).
- **Figma:** Pretendard는 본 MCP 환경에 **설치 불가**(listAvailableFonts 1723종 중 0건) → Figma DS는 **Noto Sans KR을 시각 프록시**로 사용(가용 한글 클린 산세 중 최근접; Inter는 한글 글리프 없음). **Figma 스크린샷은 타이포 메트릭(행간·자간)의 픽셀 정본이 아님** — 출고 Pretendard가 정본. (Org에 Pretendard 설치 시 Figma 텍스트스타일 일괄 교체로 프록시 해소 권장.)
- 결론: **드리프트 0** — 단일 canonical(Pretendard) + 단일 문서화 프록시(Figma Noto, 불가피) + 잔재(Cafe24) 제거 경로 확정.

## 4. ★브랜드 시그니처 + 런타임 크리에이터 테마 (결정 필요)
리뷰 최대 지적: 'Fanding computed CSS 미러 파생 → 시그니처 부재(primary #5E63F8 ≈ Stripe #635BFF)'.
**(a) 시그니처 후보 (택1~2, 대표 결정):**
1. **인디고 hue 미세 시프트** — #5E63F8 → 살짝 violet/cobalt로 틀어 'Assen 인디고' 확립(가장 저비용·안전).
2. **그라데이션 시그니처** — 히어로/CTA/스플래시에 인디고→바이올렛 메시 그라데이션(`gradient.brand`).
3. **숫자/데이터 트리트먼트** — 가격·후원액·통계에 전용 숫자 타이포(tabular, 강조 컬러) = 팬덤 '응원' 정서.
적용 표면: Splash·온보딩·EmptyState·후원/구독 완료(딜라이트 표면)로 한정, chrome은 중성 유지.
**(b) 런타임 크리에이터 액센트 토큰 (제품 개성 레버):**
```
color.creatorAccent          // 크리에이터 지정 색(런타임)
color.onCreatorAccent        // 자동 파생: APCA/WCAG로 흑/백 선택
color.creatorAccentContainer // 자동 파생: accent를 surface에 12% 틴트
color.onCreatorAccentContainer
```
- **자동 대비 보정:** 임의 액센트 입력 → WCAG 4.5(텍스트)/3.0(UI) 미달 시 자동 darken/lighten(HSL L 조정) 후 채택. onAccent는 대비 큰 쪽(흑/백) 선택.
- **침투 범위:** 프로필 헤더 배경·구독 CTA·티어 강조 **한정**(전역 primary는 인디고 유지) → 브랜드 일관성과 개성 양립.

## 5. i18n · 동적 글자 · 반응형
- **로케일:** ko(기본)/en. 통화 `₩` + 그룹 구분, 숫자 1.2k/만원 포맷 규칙, 날짜 `YYYY.MM.DD`. 텍스트 확장(en 길이) 대비 truncation(말줄임)·2줄 허용.
- **동적 글자:** OS 글자 크기 100~200% 회귀 — 고정 px 대신 텍스트 스타일 스케일 + 레이아웃 wrap 검증. 최소 130% 깨짐 없음.
- **반응형/세이프에어리어:** 브레이크포인트 compact<600(폰)·medium≥600(태블릿, ui_kit adaptive_shell 활용). `safeArea.top/bottom` 인셋 토큰 → AppBar/BottomNav/BottomCTA 적용(노치·홈인디케이터). MediaViewer 랜드스케이프 지원.

## 6. ★연령·권한 게이팅 (법무 연계)
- **연령/성인:** 본인인증 기반 연령 등급 + 19+ 콘텐츠 게이트(블러 썸네일 + "성인 인증 필요" + 인증/차단). 청소년보호 정책 연계.
- **OS 권한 프라이밍:** 카메라/사진(업로드)·알림 — 사전 설명 시트 → OS 다이얼로그 → 거부 시 복구 안내(설정 이동). 권한 거부 상태 화면.

## 7. 상태색 전략 + focus/disabled (AA 마진 보강)
- 상태색 마진이 얇음(warning 3.01·success 3.07) → **텍스트 darken 대신 필(파스텔 bg)+다크 잉크** 패턴 사용(칩과 동일). 본문 핵심은 AAA(7:1) 지향.
- `color.focusRing` = indigo 2px outline + 2px offset(WCAG 2.4.7 focus-visible). `state.disabled` = onSurface 38% + 대비 검증.
- **필 배경 텍스트 규칙:** neutral.100 필 위 보조텍스트는 ink.500(#6E6E80, 4.54:1) 사용 — ink.400은 placeholder 한정(3.09:1).

## 8. 드리프트 0 강제
마크다운 스펙 표 ↔ `tokens.v2.json` ↔ Dart 동기: (1) 마크다운 색/weight 표를 v2 값으로 갱신(또는 표 제거·JSON 단일 참조), (2) `melos run codegen:verify` 골든 회귀 + a11y 대비 매트릭스(흰/neutral.100 양 배경)를 CI 게이트화, (3) 컴포넌트 카운트·화면 카운트 단일 정본 표 유지.

## 9. 다크모드 완성
- sysDark에 `errorContainer/onErrorContainer/success/warning` 추가 완료(tokens.v2.json, 2026-06-28). 다크 시안: Home-Dark(Figma 110:461) 산출 — 나머지 핵심 화면(프로필·체크아웃·포스트상세)도 모드 전환으로 시안화 권장.

## 10. ★시그니처·크리에이터 액센트 — Figma 구현 상태 + 코드레인 계약 (8차 리뷰 반영, 2026-06-28)
8차 리뷰 FE 렌즈 지적("gradient.brand·creatorAccent가 토큰/변수 아닌 손수 칠한 fill → codegen 앵커 부재") 해소. **Figma 실앵커 구축 완료:**
- **`gradient/brand` Paint Style** (Figma 로컬 스타일, id `S:ab540ae7…`): 3-stop·커스텀 각도 — #5A4DF0(0) → #8A5CF7(0.55) → #A86CEF(1), transform≈120°. **6 표면이 전부 이 단일 스타일 참조**(Splash 89:5·Login 워드마크 87:6·CreatorHomeHeader 커버 22:4·Web-Auth 166:146·Web-CreatorProfile 157:160·PaymentComplete 98:352) → stop/각도 드리프트 0, codegen은 스타일 1개를 `gradient.brand` 토큰으로 매핑. (Figma 변수는 그라디언트 미지원이라 Paint Style로 승격.)
- **`Creator` 변수 컬렉션** (modes: `Teal`/`Coral`) + **`creator/accent` COLOR 변수**(id `224:5`; Teal #0E9E9E·Coral #E14B8A). 데모 프로필 4종(모바일 CreatorProfile-ThemeA/B 222:1326/222:1420 + 웹 Web-CreatorProfile-ThemeA/B)이 **frame 모드 오버라이드로 색 분기**, 커버/팔로우 CTA/활성탭 인디케이터가 전부 `creator/accent`에 **변수 바인딩**(다중 인스턴스 오버라이드 아님) → codegen 자동 와이어링 가능.
- **위계 (혼선 제거):** **기본 프로필 = `gradient/brand` 커버**(시그니처). **크리에이터가 액센트 지정 시 = `creator/accent` solid 커버 + CTA + 탭**(override). 즉 *기본은 그라데이션, 지정 시 단색 액센트로 치환*.
- **★코드레인 계약 (accent 출처·분류 규칙):** `creator/accent` 값의 source = **크리에이터가 스튜디오에서 직접 지정한 1색**(per-creator), **카테고리 파생 아님**. 데이터 필드 = `creator.themeColor: string(#hex, nullable)`. null이면 `gradient.brand` 기본. 런타임 파생 = §4b(`onCreatorAccent`·`creatorAccentContainer` WCAG/APCA 자동 보정 Dart 유틸). 침투 범위 = 프로필 헤더 커버·구독/팔로우 CTA·활성 탭·티어 강조 **한정**, 전역 chrome(BottomNav 등)은 인디고 유지.
- **양면 대칭:** 모바일·웹 양쪽 ThemeA/B 시연 존재(완전성 비대칭 해소). **시연 범위 = 대표 2색 정적**(다크모드/스토어 표면 전파는 런타임 책임, Figma 미시연 — 의도된 범위).
