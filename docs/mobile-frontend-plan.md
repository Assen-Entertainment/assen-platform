# 모바일(Flutter) 프론트엔드 업그레이드 계획

> 상태: 계획 정본 (2026-07-03, 프론트엔드 완결 라운드 산출물)
> 전제 문서: SDLC 10(디자인시스템·토큰), SDLC 09(도메인·API), Figma DS v2(`Snd7m8KauF51QBZL5LWuGu`)
> 현황 감사: 신방향 모바일 코드 커버리지 **0%** — 리포 내 Flutter 자산(fan_app 16화면·operator_app 7화면·ui_kit ~62위젯)은 전량 메이드era(superseded, M10 아카이브 대상)

## 1. 왜 지금 구현이 아니라 계획인가 (툴체인 게이트)

- 로컬 Windows에 flutter/dart 툴체인 없음(WSL 삭제, 2026-07-02). `dart format`·`analyze`·`test`·`flutter build` 전부 로컬 실행 불가.
- 검증 불가 상태의 Dart 코드 양산은 금지 원칙 위반 — 실증 사례: `creator_accent.dart`가 dart-format 게이트를 로컬 통과 못해 `a6c3ee1`에서 defer됨.
- 따라서 모바일 레인의 실행 조건은 다음 중 하나:
  - (a) **CI-검증 루프**: 작은 PR 단위로 GitHub Actions(Linux runner)의 format/analyze/test를 게이트로 사용 — 피드백 지연 크므로 토큰/유틸 등 소규모 작업에만 적합
  - (b) **로컬 툴체인 복구**: Windows용 Flutter SDK 직접 설치(WSL 불필요, 디스크 ~2.5GB) — 화면 구현 착수 전 권장
  - (c) WSL 재구축 — 디스크 사유로 제거했으므로 비권장

## 2. 선행 마일스톤 (착수 순서 고정)

| 순서 | 항목 | 내용 | 검증 |
|---|---|---|---|
| M1 | 토큰 v2 이관 | `tools/tokens/build.mjs:31` `TOKENS_SRC`를 `docs/design/tokens.v2.json`으로 스왑 + `CSS_NAME_MAP` 분리(랜딩 CSS는 구 tokens.json 유지 — G012 사양) → `core_tokens/*.gen.dart` 재생성 | node로 생성 가능, dart format/골든은 CI |
| M2 | creatorAccent 통일 | `web/src/lib/creator-accent.ts`(단일 파생 스펙)를 Dart로 재이관 + cross-platform 골든값 테스트(동일 입력→동일 hex) | CI |
| M3 | 앱 골격 결정·생성 | **신규 앱 `apps/platform_app` 분리 권고**(fan_app 재사용 비권고 — IA·도메인 전면 상이, 메이드 잔재 제거 비용 > 신설 비용). go_router+riverpod(기존 패턴 준용), `packages/features` auth 재사용 | CI |
| M4 | ui_kit 재편 | 메이드 템플릿 9종 격리(archive), 신규 플랫폼 organisms/templates를 웹 컴포넌트 목록(45+)과 1:1 네이밍 정합으로 신설 | CI+골든 |

## 3. Figma 04 Screens → 앱 마일스톤 맵

Figma 04 Screens ~113 프레임(도메인: 인증/홈탐색/콘텐츠/멤버십결제/커머스/후원퀘스트/소통알림/마이설정/스튜디오/상태·에러/정책)을 아래 단계로 이관한다. 프레임 전수 목록은 부록 A.

| 단계 | 범위 | 화면군 | 종료 기준 |
|---|---|---|---|
| P0 런치 코어 | 팬 소비 루프 | 온보딩/로그인·홈(디스커버리)·크리에이터 프로필(탭 4)·포스트 상세·검색 | 웹과 동일 mock API 계약(B-API) 소비, 골든+위젯 테스트 |
| P1 수익 루프 | 커머스·멤버십 | 스토어·상품상세(6타입)·체크아웃(정책 컴포넌트 포함)·주문·구독관리 | 결제=mock(#26/법무 게이트 유지) |
| P2 소셜·알림 | 커뮤니티 | 피드·댓글·알림·신고·팔로우 목록 | — |
| P3 크리에이터 | 스튜디오 | 대시보드·작성기·상품/멤버십 관리·정산 | DataTable/차트 토큰 |
| P4 폴리시 | 상태·엣지 | 빈/에러/로딩 전수·다크·a11y·딜라이트 모먼트 | 웹 루브릭 59항목의 모바일 준용판 심사 |

## 4. 웹 레인과의 정합 규약

- **디자인 토큰**: tokens.v2.json 단일 소스 — 웹(`web/scripts/build-tokens.mjs`→tokens.css)과 Dart(`tools/tokens/build.mjs`→.gen.dart)가 같은 소스를 읽어야 함(M1 완료 후 성립).
- **API 계약**: 웹 `src/lib/api/types.ts`+openapi.json(→`gen:types`)이 계약 정본 — Dart 클라이언트는 동일 openapi.json에서 생성(`api_client` 패키지 재활용).
- **creatorAccent**: 파생 알고리즘 골든값(입력 hex→accent/onAccent/container/onContainer)을 웹·Dart 공용 JSON 픽스처로 두고 양쪽 테스트가 동일 픽스처를 소비.
- **네이밍**: Figma 컴포넌트명 = 웹 ui/* = ui_kit 위젯명 3자 일치(예: MonetizableItem, StatusChip, LockedOverlay).

## 5. Linear 반영

- E12(모바일 에픽) M-이슈들에 본 계획 링크 + "커버리지 0%·툴체인 게이트" 현황 코멘트.
- M1/M2는 CI-검증 방식으로 즉시 착수 가능 백로그, M3+ 는 툴체인 복구 결정(§1-b) 후.

## 부록 A — Figma 04 Screens 프레임 전수 (113, 2026-07-03 실측)

> canvas `87:2`. 괄호는 대표 nodeId. `-Dark`/`-Empty`/`-Error` 접미는 상태·다크 변형 프레임.

- **인증 (12)**: Splash(89:5) · Login(87:3) · Login-Error · OTP · OTP-Error · Signup · Signup-Validation · Terms · PasswordReset · PasswordNew · AuthGateSheet · SessionExpired
- **온보딩 (1)**: Onboarding-Interests(91:63)
- **홈/콘텐츠 (11)**: Home(92:80) · Home-Dark · Home-Empty · Home-Loading-Skeleton · PostDetail-Public · PostDetail-Locked · PostDetail-Dark · PostComments · PostComments-Dark · MediaViewer · Announcement
- **탐색 (5)**: Search(93:131) · SearchResults · SearchResults-Empty · Category · Discovery-Curated
- **프로필 (8)**: Profile-Membership(97:188) · Profile-Membership-Dark · Profile-Store · Profile-Quest · ProfileEdit · CreatorProfile-ThemeA · CreatorProfile-ThemeB · FollowList
- **멤버십/구독 (5)**: Subscriptions(98:358) · Subscriptions-Dark · Subscriptions-Empty · SubscriptionManage · SubscriptionDunning
- **커머스/결제/환불/지갑 (25)**: ProductDetail(100:370) · ProductDetail-SoldOut · Cart · Cart-Empty · Cart-Dark · CheckoutSheet-Dark(207:1158, COMPONENT) · PaymentComplete · PaymentProcessing · PaymentFailed · PaymentFailed-Dark · PaymentMethods · PaymentMethods-Empty · OrderComplete · OrderHistory · OrderHistory-Empty · OrderCancel · DeliveryTracking · AddressManagement · RefundRequest · RefundStatus · RefundRejected · SellerRefundResponse · Recharge · Wallet
- **참여: 퀘스트/팬레터 (5)**: QuestDetail(103:440) · QuestSubmit · QuestHistory · FanLetter · FanLetterStatus
- **메시지 (3)**: MessageInbox(146:698) · MessageInbox-Empty · MessageThread
- **알림 (2)**: Notifications(104:438) · Notifications-Empty
- **마이/설정/계정/안전 (8)**: MyPage(105:440) · MyPage-Dark · Settings · Account · Withdraw · BlockList · CustomerSupport · NotificationSettings
- **정책/신고 (3)**: PolicyViewer(186:1151) · AgeGate19 · ReportComplete
- **스튜디오·정산·KYC (19)**: StudioHome(176:962) · StudioHome-Zero · PostComposer · VisibilityScopeSheet · MediaUpload · ContentManage · ProductCreate · OrderFulfillment · QuestCreate · QuestReview · MembershipCreate · TierEdit · CreatorMembers · CreatorApply · KYC-Identity · KYC-Account · Settlement · Settlement-Zero · Settlement-Dark · SettlementDetail *(Settlement 계열 포함 20이 아닌 19 — Settlement-Dark는 다크 변형으로 본 계열에 합산)*
- **전역 상태·에러/로딩 (6)**: ErrorOffline(118:529) · Error-Generic · Error-404 · PermissionDenied-403 · List-Loading-Skeleton · Detail-Loading-Skeleton

상태 커버리지 통계: 다크 변형 10 · 빈/제로 상태 10 · 로딩 스켈레톤 3 · 에러/거부 상태 11 — **모바일 구현 시 본 상태 프레임들이 P4의 종료 기준**이 된다. 프레임별 nodeId 전수는 `.omc/research/figma-inventory-2026-07-03.md`(세션 산출물) 및 Figma 파일 참조.
