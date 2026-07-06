# Assen DS 시각 게이트

빌드 → 스크린샷 → Figma 픽셀 비교. **Windows npm으로 수행**한다(구 "WSL 전용" 전제는 폐기 — ADR-10, WSL 제거됨). 코드·토큰·Figma 정합과 브랜드 루브릭은 이미 통과(정적/프로그래매틱). 이 게이트는 **런타임 시각 회귀 확인**용.

## 1. 설치 + 실행
`ASSEN_WEB_SETUP.md` §1 대로 설치 후:
```bash
npm install --legacy-peer-deps
npm run dev     # http://localhost:3000/gallery 확인
```

## 2. 스크린샷 (Playwright)
```bash
npx playwright install chromium   # playwright는 devDependency로 이미 포함
bash scripts/visual.sh            # 권장: 포트 정리→프로덕션 build/start→전 라우트 촬영
# 또는 dev 서버 위에서: node scripts/visual-gate.mjs
# → .screenshots/gallery-{light,dark,mobile}.png
# → .screenshots/screen-{discovery,creator,store,checkout}.png  (서비스 플로우)
```

## 3. Figma 기준 캡처
Figma MCP `get_screenshot`(파일 `Snd7m8KauF51QBZL5LWuGu`, 페이지 `5:3`)으로 동일 컴포넌트 캡처.

**전수 매핑(2026-07-06 R7 감사, `get_metadata` 실측)**: 코드 74 컴포넌트 ↔ Figma "02 Components" 87 디자인 컴포넌트, **매핑률 62/74 = 83.8%**. 상세 3열 표·갭·토큰 대조는 [`docs/design/ds-parity-audit-2026-07-06.md`](../docs/design/ds-parity-audit-2026-07-06.md) 참조. 아래는 시각 게이트 촬영용 주요 노드(전부 실측 확인):

| 컴포넌트 | Figma 노드 | 코드 |
|---|---|---|
| MonetizableItem | 260:28 (프레임; 256:28=굿즈 variant·258:28~72=디지털/체험/티켓/쿠폰/멤버십) | monetizable-item.tsx |
| CreatorThumbCard | 31:7 | creator-thumb-card.tsx |
| MembershipTierCard | 19:3 | membership-tier-card.tsx |
| EmptyState / ErrorState | 39:9 / 116:13 | empty-state·error-state.tsx |
| SearchField / Card / ListItem | 16:8 / 16:3 / 15:4 | search-field·card·list-item.tsx |
| Switch/Checkbox/Radio | 14:6 / 13:5 / 13:8 | switch·checkbox·radio.tsx |
| Divider/PriceLabel/Spinner/Skeleton | 12:9 / 51:10 / 50:7 / 52:8 | 각 파일 |
| Chip/Tag/StatusChip | 11:6 / 51:5 / 206:34 | chip·tag·status-chip.tsx |
| Dialog/Menu/Tabs/Tooltip/Snackbar/Toast | 83:13 / 85:14 / 109:18 / 54:10 / 116:21 / 53:13 | dialog·dropdown-menu·tabs·tooltip·toast.tsx |
| ActionSheet/BottomCTA/GiftSheet | 84:19 / 86:11 / 28:21 | sheet·bottom-cta·gift-sheet.tsx |
| AppBar/BottomNav | 17:19 / 17:3 (+BottomNavItem 64:8) | appbar·bottom-nav.tsx |
| CreatorHomeHeader/PostCard/DataTable | 22:3 / 25:15 / 214:101 | creator-home-header·post-card·data-table.tsx |
| SegmentedControl/StepIndicator/OTPInput/QuantityStepper | 85:20 / 61:16 / 62:13 / 61:9 | 각 파일 |
| SectionHeader/Pagination/CategoryIconRow | 86:15 / 202:29 / 217:77 | section-header·pagination·category-icon-row.tsx |
| Policy: ConsentGroup/DisclaimerNotice/IdentityVerifyBanner/ReportSheet/AutoPayConsentSheet/TermsLinkFooter/RefundPolicyNotice/SafetyGuideNotice | 46:24 / 41:10 / 41:15 / 42:24 / 47:9 / 47:16 / 45:16 / 45:20 | 각 파일 |
| Atoms 소형: Avatar/Badge/TextField/TextArea/Select/VerifiedMark/TextLink/ProgressBar/PriceLabel/OptionSwatch/PaymentIcon/StatItem/TimeLabel/CountLabel/LockedOverlay/SmartImage | 12:8 / 11:15 / 10:8 / 54:7 / 55:10 / 51:11 / 51:17 / 52:3 / 51:10 / 60:3 / 64:15 / 116:17 / 59:4 / 59:6 / 53:8 / 53:3 | 각 파일 |

**코드-only(Figma 미등재, 12건 — 브랜드 확정 후 등재 후보)**: accordion · file-upload · breadcrumb · calendar · date-picker · media-viewer · success-check · shelf · sidebar · topbar · right-rail · gate-note(개발전용·등재제외). 우선순위·근거는 감사 문서 §3 참조.

**Figma-only 실 갭(코드 미구현, 신규 검토)**: ProgressRing · Rating · Slider · CountdownTimer · ScrollProgressBar · QuestCard (그 외 Icon/Scrim/GradientOverlay 등은 CSS 유틸/아이콘시스템 = 컴포넌트 갭 아님).

## 4. 비교 + 수용 기준
코드 스크린샷 ↔ Figma 캡처 나란히: **색·간격·타이포·radius·elevation** 일치 확인. 차이는 아래 "의도적 편차"인지, **회귀**인지 구분 → 회귀면 수정 후 재촬영.

## 5. 알려진 의도적 편차 (브랜드 루브릭 상향 — 회귀 아님, Figma 상향 동기 권고)
동기 상태는 2026-07-06 R7 감사(`get_variable_defs` + `ds-spec-addendum §10` 앵커) 근거. 상세 근거는 [`docs/design/ds-parity-audit-2026-07-06.md`](../docs/design/ds-parity-audit-2026-07-06.md) §5.
- **CreatorThumbCard**: 이름 fs12→`title-m`, 회색 커버→`gradient.brand` 폴백 (C·B) — ⚠️ **미동기(코드 선행)**: gradient.brand Paint Style은 6표면에 바인딩되나 노드 31:7 미포함.
- **EmptyState**: 회색 서클→`primary-container` 틴트 (D) — ⚠️ **노드 fill 미확인**(변수는 실존, 39:9 바인딩 미대조).
- **MembershipTierCard**: `featured` 시 `gradient.brand` 상단 바 (B) — ⚠️ **미동기(코드 선행)**: 노드 19:3 gradient.brand 바인딩 미포함.
- **Switch**: off track `neutral-300`(=Figma #d4d4d8, 다크 `neutral-700` 대응), thumb 항상 white — ✅ **토큰값 일치**(`ref/neutral/300 = #d4d4d8` 확인; 노드 14:6 바인딩 미대조).
- **Badge success/warning**: 중립 필→`success-container`/`warning-container` filled (a11y AA) — 🟡 **부분 동기**: success-container(mint) 변수 일치. **warning은 미완** — Figma `sys/warning = #ce8509`(구값) ↔ tokens.v2 `#B8740A`(a11y 상향) **드리프트**(§4-1 참조).
- **PriceLabel**: 원가(취소선)+할인%(error) 지원 추가 — ⚠️ **코드 선행 추정**(노드 51:10 variant 미확인).

> **토큰 드리프트 1건(조치 필요)**: `sys/warning` — Figma `#CE8509`(구·비텍스트 3:1 미달) vs tokens.v2.json `#B8740A`(WCAG 1.4.11 통과). SSOT=tokens.v2. 브랜드 확정 후 Figma `sys/warning`·`ref/amber/main` 상향 동기. (그 외 sys.primary/onPrimary/primaryContainer/onPrimaryContainer/surface/onSurface/onSurfaceVariant/surfaceContainerHigh/outline/error/success + radius·spacing + 타이포 메트릭은 전부 일치.)

## 6. 체크리스트
- [ ] 라이트/다크 양모드 렌더 정상 (색 반전)
- [ ] creatorAccent 스코프 박스 대비 정상
- [ ] 오버레이(Dialog/Menu/Tooltip/Toast) 열림·포커스 트랩·스크림
- [ ] 폼 포커스 링(2px primary + offset) 일관
- [ ] 위 의도적 편차 외 Figma와 시각 일치
