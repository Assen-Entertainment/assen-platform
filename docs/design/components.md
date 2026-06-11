---
title: Assen Platform 컴포넌트 인벤토리
date: 2026-06-11
status: 기준
owner: Assen Entertainment
tags: [Design, DesignSystem, Components]
related: ["[[tokens]]", "[[references]]"]
linear: ASS-87
---

# 컴포넌트 인벤토리 v1

근거: ①실제 플랫폼 분해(위버스·버블·@home cafe·maidreamin·스타벅스·캐치테이블·토스/배민, 83종) ②M3 전체 36종 + TDS 핵심 11종 ③P0 PRD(F01~F13) 화면 분해. 상세 조사는 `research/` 및 Linear ASS-87 코멘트 참조.

## 분류 체계 — Atomic Design (2026-06-11 적용)

구조는 **Atomic Design**(Brad Frost)을 따르고, 아래 인벤토리 표의 기능 분류(Actions/Inputs/…)는 검색·매핑용 보조 축으로 유지한다.

| 레벨 | Figma 페이지 | 정의 | 현재 구성 |
|---|---|---|---|
| Foundations | `01 Tokens` | Variables(color/spacing/radius) + 텍스트 스타일 — 아원자 | 토큰 시트 |
| Atoms | `03 Atoms` | 더 쪼갤 수 없는 요소 | 18종: Button, IconButton, Checkbox, Radio, Switch, FilterChip, TimeSlotChip, Badge, CountBadge, StatusBadge, Avatar, Divider, ProgressBar, ProgressDonut, PageIndicator, FavoriteButton, Skeleton, Card |
| Molecules | `04 Molecules` | 원자 2개 이상의 단순 결합 (행·필드·셀) | 20종: TextField, SearchField, OTPField, Stepper, AgreementCell, ListItem, KeyValueRow, SectionHeader, NoticeBar, Toast, SegmentedTabs, UnderlineTabs, StepIndicator, TimelineItem, ChekiFrame, CollectionCell, CouponTicketSet, BannerCard, StatCard, EntryTicket |
| Organisms | `05 Organisms` | 화면의 독립 섹션 (구조·문맥 보유) | 15종: AppBar, TabBar, BottomCTA, BottomSheet, Dialog, EmptyState, ErrorState, MembershipCard, StampCard, ScheduleCalendar, QRDisplay, ReservationCard, EventCard, CastProfileCard, SafetyReportEntry |
| Templates | `06 Templates` | 화면 골격 — 인스턴스 조립 + placeholder 콘텐츠 | 5종: T1 홈(회원증), T2 출근표, T3 캐스트 프로필, T4 체키 앨범, T5 운영자 대시보드 |
| Pages | (P0 후반) | Templates + 실데이터 시나리오 | 콘텐츠·카피 확정 후 |
| Deprecated | `99 Deprecated` | 대체된 구버전 | InputField(→TextField), CouponTicket(→CouponTicketSet) |

레벨 판정 기준: "이 컴포넌트를 다른 화면에 그대로 옮겨도 의미가 성립하면 Organism, 부모 문맥이 있어야 의미가 생기면 Molecule, 콘텐츠 슬롯 없이 스타일만 남으면 Atom."

## 상태(variants) 규칙

- 일반: `default / pressed / disabled` (모바일 — hover 없음)
- 입력류: + `focused / error / filled`
- 선택류: + `selected`
- 테마/모드는 variants 금지 — Variables mode로만 (라이트 전용이되 시맨틱 토큰 레이어 유지로 다크 확장 가능)
- 네이밍: `property=value` variants, 8속성 초과 시 base+nested로 분해

## 한국 B2C 관례 (규칙으로 강제)

1. 화면당 주 액션 1개 = 하단 고정 CTA(BottomCTA), 키보드 위 부착
2. 선택·필터·고지는 다이얼로그 대신 바텀시트 우선 (드롭다운도 바텀시트로)
3. 약관은 전체동의 셀 + [필수]/[선택] 개별행 + 전문 화살표
4. 정보성/광고성 푸시 토글 분리 + 변경 시 일시 고지 토스트 (정보통신망법)
5. 본인인증 표준 플로우: 약관 → 통신사(바텀시트) → 번호 → OTP 6자리 → 완료 화면
6. D-day 표기 토큰 통일 (D+N/D−N) — 단 "관계 기념일" 프레임 금지(references 금지 패턴), 방문·유효기간 중심

## 인벤토리

표기: ✅=Figma 완료 / 🔨=이번 배치 / P1·P2=해당 단계에서 제작 (flag off 기능용)

### Actions
| 컴포넌트 | 우선순위 | variants | 상태 |
|---|---|---|---|
| Button | P0 | style=primary/secondary/ghost (+state는 P0 후반 추가) | ✅ |
| IconButton | P0 | default/pressed/disabled | 🔨 |
| BottomCTA | P0 | 단일/2분할, 활성/비활성 — 한국 관례 #1 | 🔨 |
| FAB | P1 (팬 글쓰기 없음 — P0 불필요) | — | P1 |

### Inputs
| 컴포넌트 | 우선순위 | variants | 상태 |
|---|---|---|---|
| TextField | P0 | default/focused/error/disabled (기존 InputField 대체) | 🔨 |
| SearchField | P0 | default/focused | 🔨 |
| Checkbox | P0 | checked/unchecked/disabled | 🔨 |
| Radio | P0 | selected/unselected/disabled | 🔨 |
| Switch | P0 | on/off/disabled | 🔨 |
| FilterChip | P0 | selected/unselected (+count) — 수집 필터·출근표 날짜 | 🔨 |
| AgreementCell | P0 | 전체동의/개별([필수]·[선택]) — 한국 관례 #3 | 🔨 |
| Stepper | P0 | default/min/max — 예약 인원 | 🔨 |
| OTPField | P0 | 입력중/완료/오류 — 본인인증 | 🔨 |
| MessageInputBar | P2 | 메시지는 P2 기능 | P2 |
| Rating | — | 공개 리뷰는 P0 비목표 | 보류 |

### Navigation
| 컴포넌트 | 우선순위 | variants | 상태 |
|---|---|---|---|
| AppBar | P0 | 기본형 (센터 타이틀) | ✅ |
| TabBar(Bottom) | P0 | 4탭, active 표시 | ✅ |
| SegmentedTabs | P0 | 2분할 selected/unselected — 운영자 화면 전환 | 🔨 |
| UnderlineTabs | P0 | 가로 스크롤형 — 캐스트/이벤트 목록 | 🔨 |
| PageIndicator | P0 | dots — 배너 캐러셀 | 🔨 |
| SectionHeader | P0 | 액션 유/무 ("전체보기 ›") | 🔨 |
| StepIndicator | P0 | 가입·예약 플로우 점형 | 🔨 |

### Containment
| 컴포넌트 | 우선순위 | variants | 상태 |
|---|---|---|---|
| ListItem | P0 | 기본 (chevron) — 추후 값표시/토글내장 확장 | ✅ |
| Card(generic) | P0 | level0(보더)/level1(그림자) | 🔨 |
| BottomSheet | P0 | 핸들+타이틀+콘텐츠+CTA — 한국 관례 #2 | 🔨 |
| Dialog | P0 | 1버튼/2버튼(파괴적=red) | 🔨 |
| KeyValueRow | P0 | 기본/강조 — 예약 상세·POS 정보 | 🔨 |
| Divider | P0 | 풀폭/인셋 | 🔨 |
| NoticeBar | P0 | info/warning — 공지 띠 | 🔨 |

### Feedback
| 컴포넌트 | 우선순위 | variants | 상태 |
|---|---|---|---|
| Toast | P0 | 텍스트/아이콘+텍스트/액션 포함 | 🔨 |
| EmptyState | P0 | 문구만/+CTA — 쿠폰·체키·예약 빈 화면 | 🔨 |
| ErrorState | P0 | 재시도 포함 | 🔨 |
| Skeleton | P0 | 리스트형/카드형 | 🔨 |
| ProgressBar | P0 | 선형 — 스탬프·목표 진행 | 🔨 |
| ProgressDonut | P0 | 원형 — 방문 진행(등급 3종 세트 패턴) | 🔨 |
| StatusBadge | P0 | 확정(matcha)/대기(lemon)/완료(sky)/취소(red) — 예약·신고 상태 | 🔨 |
| LoadingSpinner | P0 | 인라인/풀스크린 | P0 후반 |
| SuccessScreen | P0 | 가입·예약 완료 풀스크린 — 토스 관례 | P0 후반 |
| CoachMark/Tooltip | P1 | — | P1 |

### Content
| 컴포넌트 | 우선순위 | variants | 상태 |
|---|---|---|---|
| Avatar | P0 | size S/M/L + 캐스트 컬러 링 + 출근중 점 | 🔨 |
| BannerCard | P0 | 홈 배너 캐러셀 (+PageIndicator) | 🔨 |
| Badge | P0 | hue 6종 | ✅ |
| CountBadge | P0 | 숫자(99+)/점 — 탭·알림 | 🔨 |
| TimelineItem | P0 | 날짜 그룹+항목 — 방문/포인트 내역 | 🔨 |
| RankingItem | P1 | 공개 랭킹은 P0 금지(안전 제약) — 운영자 내부용만 P1 | P1 |

### Domain (메이드카페 특화)
| 컴포넌트 | 우선순위 | variants | 상태 |
|---|---|---|---|
| MembershipCard | P0 | skin 3종 (strawberry/sky/lavender) | ✅ |
| QRDisplay | P0 | 회전 QR + 갱신 타이머 링 + 만료 — 휘도 자동 상향 명세 | 🔨 |
| ChekiFrame | P0 | 기본 (앨범 셀 겸용) | ✅ |
| CollectionCell | P0 | 획득/미획득(실루엣+잠금)/NEW — 체키·배지 수집 그리드 | 🔨 |
| StampCard | P0 | 8칸 (채움/빈칸/리워드) | ✅ |
| CouponTicket | P0 | 사용가능/사용완료/만료 — 기존 단일 → 세트 확장 | 🔨 |
| CastProfileCard | P0 | 기본/최애♥/출근중 | 🔨 |
| FavoriteButton | P0 | on/off 하트 토글 — 최애 등록 | 🔨 |
| ScheduleCalendar | P0 | 주간 스트립: 이벤트점/선택/오늘/휴무 | 🔨 |
| TimeSlotChip | P0 | 가용/마감(취소선)/선택 — 예약 | 🔨 |
| PartySizeChip | P0 | 인원 선택 | 🔨 (FilterChip 재사용+라벨) |
| ReservationCard | P0 | 다가옴(D-day)/방문완료/취소 | 🔨 |
| EntryTicket | P0 | 대기중/호출됨(강조)/입장완료 — @home 앗토엔트리 패턴 | 🔨 |
| VisitLogItem | P0 | 방문 행: 스탬프 모티프+날짜+만난 캐스트 (TimelineItem 변형) | 🔨 |
| EventCard | P0 | 예정(D−N)/진행중/종료 + 예약 CTA | 🔨 |
| SafetyReportEntry | P0 | 신고 진입 셀 — 캐스트/팬 화면 상시 노출 | 🔨 |
| PointHistoryCell | P0 | 적립(+)/사용(−)/소멸예정 | 🔨 (TimelineItem 변형) |
| StatCard | P0 | 운영자 대시보드 일일 지표 | 🔨 |
| MessageBubble | P2 | 1:N 피드 — 읽음 환상·닉네임 치환 금지 제약 | P2 |
| SubscriptionCell / PackageCard / BalanceWidget | P1 | 결제·멤버십 — flag off | P1 |
| TierCard(등급 안내) | P1 | P0는 등급제 제외 | P1 |
| MissionCard / TrophyGrid 확장 | P1 | 게이미피케이션 확장 | P1 |

## 집계 (2026-06-11 기준)

- Figma 제작 완료: Atoms 18 + Molecules 20 + Organisms 15 = **53종 (variants 118개)** + Templates 5종
- P0 후반 잔여 4종: LoadingSpinner, SuccessScreen 등 — Pages 단계에서
- P1 9종 / P2 2종 / 보류 1종 — 에픽 진행 시 제작
- Deprecated 2종: InputField·CouponTicket (세트로 대체)
- Templates 한계: 인스턴스 placeholder 콘텐츠 공유(StatCard 동일 수치 등) — Pages 단계에서 텍스트 오버라이드

## 미해결

- 아이콘 세트: P0 후반 결정 (Material Symbols 기본 + 도메인 아이콘 커스텀 — 체키·스탬프·하트)
- maidreamin 트로피·위버스 멤버십 카드 실기기 스크린샷 QA (추정 표기 항목 검증)
- 운영자 콘솔 전용 컴포넌트(DataTable·FilterBar)는 대시보드 화면 설계 시 확정
