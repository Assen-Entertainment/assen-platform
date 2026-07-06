---
title: DS 패리티 감사 — 코드 ↔ Figma 컴포넌트/토큰 정합 (R7, ASS-255)
date: 2026-07-06
branch: feature/r7-mobile-close
status: 읽기 감사 산출. Figma 파괴적 쓰기 없음(브랜드 방향 E9 미확정). 등재는 브랜드 확정 후행.
related:
  - "[[tokens.v2.json]]"
  - "[[ds-spec-addendum-2026-06-28.md]]"
  - "[[ASSEN_DS_VISUAL_GATE.md]]"
figma:
  fileKey: Snd7m8KauF51QBZL5LWuGu
  page: "02 Components (5:3)"
  auth: owsqix (pro, expert seat) — whoami 확인됨
---

# DS 패리티 감사 (2026-07-06)

## 0. 방법 · 근거

| 근거 | 도구 | 범위 |
|---|---|---|
| 코드 인벤토리 | `web/src/components/ui/index.ts` 배럴 + `*.tsx` glob | 74개 컴포넌트 모듈(테스트·`use-toast` 훅 제외) |
| Figma 노드 전수 | `get_metadata`(fileKey, node `5:3`) | "02 Components" 5개 섹션 전 노드 실측 |
| 토큰 변수 스팟 | `get_variable_defs`(node `43:3` Atoms) | color/spacing/radius/typography 실바인딩 33개 |
| 변수 라이브러리 확인 | `search_design_system` | `Assen Platform DS v2 — Fanding Redesign`(Primitives+Semantic 컬렉션) 존재 확인 |

**근거 규율**: 실제 대조한 값만 "일치"로 표기. `get_screenshot` 픽셀 비교는 이 감사 범위 밖(런타임 시각 게이트가 담당) — 편차 동기 상태는 토큰 변수 바인딩·`ds-spec-addendum §10` 앵커 기록을 근거로 판정하고, 노드 fill 바인딩 미확인 항목은 "미확인"으로 명시.

## 1. 요약 수치

| 지표 | 값 |
|---|---|
| 코드 DS 컴포넌트(ui/, 테스트·훅 제외) | **74** |
| Figma "02 Components" 디자인 컴포넌트(ic-* 아이콘 글리프 13종 제외) | **87** |
| 코드 ↔ Figma 매핑됨 | **62 / 74 = 83.8%** |
| 코드-only(Figma 미등재) | **12** |
| Figma-only(코드 ui/ 미구현) — 실 갭 | **10** (그 외 ~10은 CSS 유틸/하위요소/아이콘시스템으로 의도적 비-컴포넌트) |
| 토큰 스팟 대조 | 32/33 일치, **1 드리프트**(`sys/warning`) + 폰트 프록시 1(의도적) |

핵심: 매핑률 83.8%, **코드-only 12건이 Figma 등재 후보**, **토큰 드리프트 1건(warning 색)** 확인.

---

## 2. (a) 코드 ↔ Figma 3열 매핑 표

상태 범례: ✅ 매핑됨 · 🟡 상위/하위 노드 대응(부분) · ⬜ 코드-only(Figma 미등재)

### Atoms
| 코드 파일 | Figma 노드 | 상태 |
|---|---|---|
| button.tsx | Button `9:8` (variants 9:2/9:4/9:6/77:2/78:2/78:4) | ✅ |
| textfield.tsx | TextField `10:8` (Default/Focused/Error/Disabled) | ✅ |
| chip.tsx | Chip `11:6` | ✅ |
| badge.tsx | Badge `11:15` (Neutral/Primary/Success/Error) | ✅ |
| avatar.tsx | Avatar `12:8` (S/M/L) | ✅ |
| divider.tsx | Divider `12:9` | ✅ |
| checkbox.tsx | Checkbox `13:5` | ✅ |
| radio.tsx | Radio `13:8` | ✅ |
| switch.tsx | Switch `14:6` (Off/On) | ✅ |
| spinner.tsx | Spinner `50:7` | ✅ |
| tag.tsx | Tag `51:5` | ✅ |
| price-label.tsx | PriceLabel `51:10` | ✅ |
| verified-mark.tsx | VerifiedMark `51:11` | ✅ |
| text-link.tsx | TextLink `51:17` | ✅ |
| progress-bar.tsx | ProgressBar `52:3` | ✅ |
| skeleton.tsx | Skeleton `52:8` | ✅ |
| smart-image.tsx | Image `53:3` (이미지 프리미티브) | ✅ |
| locked-overlay.tsx | LockedOverlay `53:8` | ✅ |
| toast.tsx | Toast `53:13` + Snackbar `116:21` | ✅ (2노드) |
| text-area.tsx | TextArea `54:7` | ✅ |
| tooltip.tsx | Tooltip `54:10` | ✅ |
| select.tsx | Select `55:10` | ✅ |
| time-label.tsx | TimeLabel `59:4` | ✅ |
| count-label.tsx | CountLabel `59:6` | ✅ |
| option-swatch.tsx | OptionSwatch `60:3` | ✅ |
| payment-icon.tsx | PaymentIcon `64:15` | ✅ |
| stat-item.tsx | StatItem `116:17` | ✅ |
| status-chip.tsx | StatusChip `206:34` (완료/진행중/실패/대기) | ✅ |

### Molecules
| 코드 파일 | Figma 노드 | 상태 |
|---|---|---|
| list-item.tsx | ListItem `15:4` | ✅ |
| card.tsx | Card `16:3` | ✅ |
| search-field.tsx | SearchField `16:8` | ✅ |
| creator-thumb-card.tsx | CreatorThumbCard `31:7` | ✅ |
| empty-state.tsx | EmptyState `39:9` | ✅ |
| quantity-stepper.tsx | QuantityStepper `61:9` | ✅ |
| step-indicator.tsx | StepIndicator `61:16` | ✅ |
| otp-input.tsx | OTPInput `62:13` | ✅ |
| segmented-control.tsx | SegmentedControl `85:20` | ✅ |
| section-header.tsx | SectionHeader `86:15` | ✅ |
| error-state.tsx | ErrorState `116:13` | ✅ |
| pagination.tsx | Pagination `202:29` | ✅ |
| category-icon-row.tsx | CategoryIconRow `217:77` | ✅ |

### Organisms
| 코드 파일 | Figma 노드 | 상태 |
|---|---|---|
| bottom-nav.tsx | BottomNavBar `17:3` (+ BottomNavItem `64:8`) | ✅ |
| appbar.tsx | AppBar `17:19` | ✅ |
| membership-tier-card.tsx | MembershipTierCard `19:3` | ✅ |
| creator-home-header.tsx | CreatorHomeHeader `22:3` | ✅ |
| post-card.tsx | PostCard `25:15` | ✅ |
| gift-sheet.tsx | GiftSheet `28:21` | ✅ |
| dialog.tsx | Dialog `83:13` (+ Modal `117:17` 대형) | 🟡 1코드=2노드 |
| sheet.tsx | ActionSheet `84:19` | ✅ |
| dropdown-menu.tsx | Menu `85:14` | ✅ |
| bottom-cta.tsx | BottomCTA `86:11` | ✅ |
| tabs.tsx | Tabs `109:18` (+ TabItem `55:14`) | ✅ |
| data-table.tsx | DataTable `214:101` (Default/Empty/Loading) | ✅ |
| monetizable-item.tsx | MonetizableItem `260:28` (굿즈256:28/디지털258:28/체험258:39/티켓258:50/쿠폰258:61/멤버십258:72) | ✅ |

### Policy / Compliance
| 코드 파일 | Figma 노드 | 상태 |
|---|---|---|
| consent-group.tsx | ConsentGroup `46:24` (+ ConsentRow `41:7`) | ✅ |
| disclaimer-notice.tsx | DisclaimerNotice `41:10` | ✅ |
| identity-verify-banner.tsx | IdentityVerifyBanner `41:15` | ✅ |
| report-sheet.tsx | ReportSheet `42:24` | ✅ |
| auto-pay-consent-sheet.tsx | AutoPayConsentSheet `47:9` | ✅ |
| terms-link-footer.tsx | TermsLinkFooter `47:16` | ✅ |
| refund-policy-notice.tsx | RefundPolicyNotice `45:16` | ✅ |
| safety-guide-notice.tsx | SafetyGuideNotice `45:20` | ✅ |

### 코드-only (Figma 미등재) — ⬜
| 코드 파일 | 성격 | Figma 노드 |
|---|---|---|
| accordion.tsx | 범용 폼/콘텐츠 | 없음 |
| file-upload.tsx | 업로드 폼 | 없음 |
| breadcrumb.tsx | 내비 | 없음 |
| calendar.tsx | 날짜(R6-W2D 자체구현) | 없음 |
| date-picker.tsx | 날짜(R6-W2D 자체구현) | 없음 |
| media-viewer.tsx | 라이트박스(W4) | 없음(Image/Scrim/GradientOverlay 조합) |
| success-check.tsx | 딜라이트 애니(W4) | 없음 |
| shelf.tsx | 수평 스크롤러 | 없음 |
| sidebar.tsx | 웹 데스크톱 셸 | 없음(AppBar=모바일) |
| topbar.tsx | 웹 데스크톱 셸 | 없음(AppBar=모바일) |
| right-rail.tsx | 웹 데스크톱 셸 | 없음 |
| gate-note.tsx | 개발 전용(`SHOW_GATE_NOTES` 플래그) | 없음 — DS 컴포넌트 아님 |

> §3 표(ASSEN_DS_VISUAL_GATE.md) 대조: 기존 매핑 22노드는 `get_metadata` 실측과 전부 일치. 유일 정밀화 — MonetizableItem은 표에 `256:28`(=굿즈 variant)로 기재되어 있었으나 컴포넌트 프레임은 `260:28`이며 256:28은 그 하위 굿즈 variant. 나머지(31:7·19:3·39:9·16:8·14:6·13:5·13:8·12:9·51:10·50:7·52:8·83:13·85:14·109:18·54:10·116:21·17:19·17:3·15:4·12:8·11:15) 전부 정확.

---

## 3. (b) 갭 분석

### 3-1. 코드-only 12건 = Figma 등재 후보 (우선순위)
| 우선 | 컴포넌트 | 근거 |
|---|---|---|
| **P1** | accordion, file-upload, date-picker, calendar, breadcrumb | 범용·양 플랫폼 재사용, 폼/내비 핵심. 브랜드 확정 후 최우선 등재 |
| **P2** | media-viewer, success-check, shelf | 기능성·단일 표면. media-viewer는 Image/Scrim/GradientOverlay 프리미티브 조합으로 구성 가능 |
| **P3** | sidebar, topbar, right-rail | 웹 데스크톱 셸 전용(모바일 무관). Figma는 모바일 셸(AppBar/BottomNav) 중심 → 웹 셸 프레임 신설 시 등재 |
| **P4** | gate-note | 개발 전용 계측 헬퍼. **DS 등재 대상 아님**(제외 권고) |

→ 실 등재 대상 = P1~P3 **11건** (gate-note 제외).

### 3-2. Figma-only (코드 ui/ 미구현)
**(가) 실 갭 — 디자인만 있고 코드 컴포넌트 없음 (10)**: ProgressRing `52:5`, Rating `54:17`, Slider `55:3`, CountdownTimer `59:9`, ScrollProgressBar `64:3`, ProductCard `38:14`(→ MonetizableItem이 상위 대체 가능성), FilterChipRow `109:30`(→ Chip 조합으로 대체 중), QuestCard `27:13`(퀘스트 기능 미구현), CheckoutSheet `30:19`(체크아웃=앱 라우트 조합, ui/ 비대상), AgeGate `45:12`(연령 게이트=locked-overlay+게이팅 로직 조합).
→ 이 중 순수 신규 필요 후보: **ProgressRing, Rating, Slider, CountdownTimer, ScrollProgressBar, QuestCard**. 나머지 4(ProductCard/FilterChipRow/CheckoutSheet/AgeGate)는 기존 코드로 대체·조합 중 → 등재 불요 또는 통합.

**(나) 의도적 비-컴포넌트 — Figma는 프리미티브로 문서화, 코드는 유틸/내재 (10)**: Icon `50:3`·IconButton `50:5`(아이콘 시스템=lucide-react), GradientOverlay `60:4`·LineClamp `64:12`·Scrim `53:9`(CSS 유틸), PaginationDot `52:13`·HelperText `51:15`·StatusDot `50:9`·Label `59:13`·InlineTag `64:14`(부모 컴포넌트 내재 또는 Tag 중복). → **갭 아님**.

---

## 4. (c) 토큰 Variables ↔ tokens.v2.json 스팟 대조

`get_variable_defs`(Atoms `43:3`)로 실바인딩된 값 vs `tokens.v2.json`:

| 토큰 | Figma 변수 | tokens.v2.json | 판정 |
|---|---|---|---|
| sys/primary | `#5a4df0` | indigo.500 `#5A4DF0` | ✅ 일치 |
| sys/onPrimary | `#ffffff` | white | ✅ 일치 |
| sys/primaryContainer | `#efeffe` | indigo.100 `#EFEFFE` | ✅ 일치 |
| sys/onPrimaryContainer | `#2e2c8a` | indigo.ink `#2E2C8A` | ✅ 일치 |
| sys/surface | `#ffffff` | white | ✅ 일치 |
| sys/onSurface | `#191919` | ink.900 `#191919` | ✅ 일치 |
| sys/onSurfaceVariant | `#6e6e80` | ink.500 `#6E6E80` | ✅ 일치 |
| sys/surfaceContainerHigh | `#f4f4f5` | neutral.100 `#F4F4F5` | ✅ 일치 |
| sys/outline | `#e9e9f1` | neutral.200 `#E9E9F1` | ✅ 일치 |
| sys/error | `#d73d3d` | red.main `#D73D3D` | ✅ 일치 |
| sys/success | `#1da951` | green.main `#1DA951` | ✅ 일치 |
| **sys/warning** | **`#ce8509`** | **amber.main `#B8740A`** | ❌ **드리프트** |
| radius xs/sm/md/full | 4/8/12/999 | 4/8/12/999 | ✅ 일치 |
| spacing 1/2/3/4/5 | 4/8/12/16/20 | 4/8/12/16/20 | ✅ 일치 |
| ref ink.500·neutral.100·neutral.300·indigo.500·indigo.100·mint.bg/ink·red.bg/ink·white | (실측) | (동일) | ✅ 일치 |
| Type/Label, Type/Body/M, Type/Caption | Noto Sans KR 14·15·12 (500/400/500), lh 20·23·16 | label·bodyM·caption 14·15·12, lh 1.43·1.53·1.33 | ✅ 메트릭 일치 (폰트=프록시) |

### 4-1. 드리프트 1건 (조치 필요)
- **`sys/warning`: Figma `#CE8509` ↔ tokens.v2.json `#B8740A`.**
  - tokens.v2.json은 a11y 사유로 `#CE8509`(비텍스트 3:1 미달: white 3.01·cream 컨테이너 2.86)를 `#B8740A`(white 3.79 / cream.bg 3.61, WCAG 1.4.11 통과)로 **이미 상향**. Figma 변수는 구값(`#CE8509`) 잔존.
  - **SSOT=tokens.v2.json.** → 브랜드 확정 후 Figma `sys/warning` 및 `ref/amber/main` 변수를 `#B8740A`로 상향 동기 필요. Badge warning-container·경고 배지 표면에 영향.

### 4-2. 드리프트 아님(의도적, 문서화됨)
- **폰트 = Noto Sans KR**: Figma 텍스트 변수는 Noto Sans KR. tokens.v2.json canonical = Pretendard Variable. `ds-spec-addendum §3-1`에 **의도적 프록시**(Pretendard 본 MCP 환경 미설치 → 가용 한글 산세 최근접)로 명문화. 출고 Pretendard가 정본, Figma 메트릭은 픽셀 정본 아님 → **드리프트 0**.
- 미샘플 항목(`sys/secondary` 등 ink.600 계열)은 Atoms 스팟 세트에 미출현 → 이번 감사 "확인" 범위 밖(불일치 아님, 미확인).

---

## 5. (d) §5 의도적 편차 — Figma 상향동기 상태

`ASSEN_DS_VISUAL_GATE.md §5`는 6건(문서상 "5건" 표기는 오기, 실제 6 bullet). 근거=토큰 변수 바인딩 + `ds-spec-addendum §10` 앵커 기록.

| # | 편차 | Figma 동기 상태 | 근거 |
|---|---|---|---|
| 1 | CreatorThumbCard: 이름 fs12→title-m, 회색 커버→gradient.brand 폴백 | ⚠️ **미동기 추정** | §10 gradient.brand Paint Style은 6표면에 바인딩(Splash·Login·CreatorHomeHeader 22:4·Web-Auth·Web-CreatorProfile·PaymentComplete) — **CreatorThumbCard 31:7은 목록에 없음** → 코드 선행 |
| 2 | EmptyState: 회색 서클→primary-container 틴트 | ⚠️ **노드 fill 미확인** | primaryContainer 변수(`#efeffe`)는 존재. EmptyState 39:9의 서클 fill 바인딩 미확인 → get_screenshot/노드 대조 필요 |
| 3 | MembershipTierCard: featured 시 gradient.brand 상단 바 | ⚠️ **미동기 추정** | §10 gradient.brand 바인딩 표면에 19:3 미포함 → 코드 선행 |
| 4 | Switch: off track neutral-300 | ✅ **토큰값 일치**(노드 바인딩 미확인) | `ref/neutral/300 = #d4d4d8` 변수 실존 확인. Switch 14:6 State=Off의 track이 이 변수를 바인딩하는지는 미확인 |
| 5 | Badge success/warning: 중립필→success/warning-container filled | 🟡 **부분 동기** | success-container(mint.bg/ink) 변수 존재·일치. **warning은 §4-1 드리프트(`sys/warning` 구값)로 미완** |
| 6 | PriceLabel: 원가(취소선)+할인%(error) 지원 | ⚠️ **코드 선행 추정** | PriceLabel 51:10 존재하나 취소선/할인% variant 유무 미확인 → 코드가 기능 확장 선행 |

**정리**: 6건 중 **완전 동기 0 · 값일치(부분) 2(#4·#5 일부) · 미동기/코드선행 4**. gradient.brand 계열(#1·#3) 및 PriceLabel(#6)은 코드가 브랜드 상향을 선행 → 브랜드 확정 시 Figma 노드에 반영 대상. warning(#5) 드리프트는 §4-1과 연동.

---

## 6. 다음 액션 (브랜드 방향 E9 확정 후)

1. **토큰 동기 1건**: Figma `sys/warning`·`ref/amber/main` → `#B8740A` 상향(tokens.v2 SSOT 정합).
2. **Figma 신규 등재 11건**(코드-only, gate-note 제외): P1(accordion·file-upload·date-picker·calendar·breadcrumb) → P2(media-viewer·success-check·shelf) → P3(sidebar·topbar·right-rail).
3. **의도적 편차 Figma 반영 4건**: CreatorThumbCard/MembershipTierCard gradient.brand 커버·상단바(#1·#3), PriceLabel 취소선/할인% variant(#6), EmptyState primary-container 틴트(#2) — 노드 스크린샷 대조 후.
4. **신규 컴포넌트 검토 6건**(Figma-only 실갭): ProgressRing·Rating·Slider·CountdownTimer·ScrollProgressBar·QuestCard — 로드맵 편입 여부 판단.
5. **모두 브랜드 확정 후행** — 현 시점 Figma 파괴적 쓰기 금지 유지.
