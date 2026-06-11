---
title: Assen Platform 디자인 토큰 스펙 v0.1
date: 2026-06-11
status: 초안(리뷰 대기)
owner: Assen Entertainment
tags: [Design, Tokens, DesignSystem, Hatsukoi]
related: ["[[references]]", "[[CONSTRAINTS]]"]
linear: ASS-85
---

# 디자인 토큰 스펙 v0.1 — 하츠코이 라이트 레트로 큐트

확정 방향(2026-06-11): Assen Platform 우산 브랜드 / 라이트 전용(다크 확장 가능 구조) / 크림+파스텔 멀티컬러 / 솔리드 컬러(그라디언트 금지) / 일러스트 없이 모티프 시스템.
기계 포맷: `tokens.json` (W3C DTCG Design Tokens Format 2025.10). 파이프라인: 본 스펙 → Figma(Tokens Studio Variables) → `packages/design_system` (Style Dictionary → Dart 상수 + 수동 ColorScheme + ThemeExtension).

## 원칙

1. **파스텔은 전경 금지.** 파스텔은 배경·필·배지 전용이며, 텍스트·아이콘은 잉크 램프 또는 각 hue의 ink 스텝만 쓴다 (WCAG AA — 파스텔 텍스트는 1.3~2:1로 전면 실패).
2. **hue당 4스텝 트리플+1**: `bgSubtle / bg / border / ink`. 배지·칩 = 동일 hue의 bg+ink 조합. 파스텔 면이 인접하면 반드시 border 스텝으로 구분(비텍스트 대비 3:1).
3. **크림 보정**: 배경이 순백이 아니라 크림(#FFFDF7~#FFF8E7)이므로 대비가 ~5% 손실된다. 본문 잉크는 ink-700 이상, 보조 텍스트도 ink-500 미만 금지.
4. **시맨틱과 장식의 분리**: `sys.*`(M3 역할 — 화면 구조·상태)와 `decorative.*`(파스텔 멀티컬러·캐스트 컬러 — ThemeExtension)를 다른 네임스페이스로. 장식 토큰에는 텍스트 역할이 구조적으로 없다.
5. **위계는 어두워지지 않는다**: 상위 등급 표현은 블랙+골드 클리셰 대신 우표 색·스탬프 밀도·프레임 장식 증가로 (references 금지 패턴 #6).
6. **모티프 색 3색 이내** (@home 데코 원칙 차용).
7. surfaceTint 비활성(M3 틴트가 크림을 왜곡), 그림자는 2단계만 — 구분은 기본적으로 보더가 한다.

## 1. color.ref — 원시 팔레트

### 크림·잉크 (단일 계열)

| 토큰 | 값 | 용도 |
|---|---|---|
| cream.50 | #FFFDF7 | 앱 배경 |
| cream.100 | #FFF8E7 | 보조 서피스, 컨테이너 high |
| cream.200 | #F8EFDB | subtle fill, hover |
| cream.300 | #EFE3C9 | pressed fill |
| white | #FFFFFF | 카드 서피스 (크림 위에서 떠 보이게) |
| ink.900 | #2B2724 | 본문·제목 (크림 위 ~14:1) |
| ink.700 | #57534E | 보조 텍스트 (~7:1) |
| ink.500 | #8A8178 | 비활성·힌트 (~4.6:1, 본문 금지) |
| ink.300 | #C9C0B4 | 강한 보더·디바이더 |
| ink.200 | #E3DACA | outline |
| ink.100 | #F0EADD | outlineVariant |

### 파스텔 6 hue (bgSubtle / bg / border / ink)

| hue | bgSubtle | bg | border | ink | 비고 |
|---|---|---|---|---|---|
| strawberry | #FFF0F4 | #FFD9E2 | #F0A8BC | #8E2F4A | 하츠코이(初恋) 키 — primary 계열 |
| peach | #FFF2E9 | #FFDCC7 | #EBAF85 | #8A4A1F | |
| lemon | #FFF9DF | #FFEFB3 | #DDC25E | #6E5A14 | |
| matcha | #EFF6EA | #D8EBCB | #A0CC89 | #3E6132 | success 겸용 |
| sky | #EAF5F9 | #CFE9F2 | #92C6D9 | #1F566B | 랜딩 blue(#7eb8ca) 연결 |
| lavender | #F4F0FA | #E2DAF4 | #BCA9E3 | #54408A | |

- 각 ink는 자기 bg 위에서 4.5:1 이상이 되도록 선정(예: #8E2F4A on #FFD9E2 ≈ 6.2:1). Figma 구축 시 전 조합 콘트라스트 검수(ASS-87 수용 기준).
- 캐스트 컬러는 이 6 hue를 슬롯으로 배정한다(응원색 문화 — references 채택 #11). 캐스트 수가 6을 넘으면 hue 추가는 동일 4스텝 규칙으로.

### 브랜드·상태

| 토큰 | 값 | 용도 |
|---|---|---|
| brass.bg | #F6ECD9 | Assen 브랜드 면 (랜딩 #d4a24f 연결) |
| brass.main | #D4A24F | 장식 라인·아이콘 (텍스트 금지) |
| brass.ink | #6E5224 | brass 면 위 텍스트 |
| red.main | #B64650 | error (랜딩 red 재사용) |
| red.bg | #FFE1E4 | errorContainer |
| red.ink | #7A2530 | onErrorContainer |

## 2. color.sys — M3 역할 매핑 (라이트 단일, 수동 ColorScheme)

| 역할 | 값 | | 역할 | 값 |
|---|---|---|---|---|
| surface | cream.50 | | primary | #C2486B |
| surfaceContainer | white | | onPrimary | #FFFFFF |
| surfaceContainerHigh | cream.100 | | primaryContainer | strawberry.bg |
| onSurface | ink.900 | | onPrimaryContainer | strawberry.ink |
| onSurfaceVariant | ink.700 | | secondary | brass.ink |
| outline | ink.200 | | secondaryContainer | brass.bg |
| outlineVariant | ink.100 | | tertiary | sky.ink |
| error | red.main | | tertiaryContainer | sky.bg |
| onError | #FFFFFF | | surfaceTint | 사용 안 함 |

- primary #C2486B: 파스텔이 아닌 **솔리드 로즈** — CTA·활성 상태 전용 앵커(흰 텍스트 ~4.9:1). 파스텔 멀티컬러 속에서 행동 유도는 단일 색으로 고정.
- 다크 확장: ref 램프에 다크 값을 추가하는 방식으로 확장 가능하게 구조만 유지(P0 비범위).

## 3. typography

| 슬롯 | 폰트 | 크기/행간 | 용도 |
|---|---|---|---|
| display.l | 카페24 써라운드 | 36/46 | 풀스크린 축하, 온보딩 타이틀 |
| display.m | 카페24 써라운드 | 28/38 | 화면 히어로 |
| headline | 카페24 써라운드 | 22/30 | 섹션 타이틀 |
| title.l | Pretendard SemiBold | 19/27 | 카드 타이틀 |
| title.m | Pretendard SemiBold | 16/24 | 리스트 타이틀 |
| body.l | Pretendard | 16/26 | 본문 강조 |
| body.m | Pretendard | 14/22 | 기본 본문 (한국어 행간 1.55+) |
| body.s | Pretendard | 12/18 | 보조 설명 |
| label | Pretendard Medium | 13/18 | 버튼·칩·탭 |
| pixel | 갈무리11 (Galmuri) | 11/16 | 일련번호·스탬프 번호·장식 캡션 한정 |
| serif-formal | (랜딩 Fraunces 계열, 한글은 추후 결정) | — | 등급명·증서 등 격식 표면 한정 (투트랙 원칙) |

- 라이선스 전부 검증 완료(OFL/임베드 허용): Pretendard, 카페24 써라운드, 갈무리. 숫자·라틴 보조로 Space Grotesk(OFL) 후보.
- serif-formal의 한글 폰트는 미정 — Figma 단계에서 후보 비교(ASS-87).

## 4. spacing / radius / elevation / motion

- **spacing** (4dp 베이스): 4, 8, 12, 16, 20, 24, 32, 40, 48, 64. 화면 마진 20, 카드 내부 16, 체키 그리드 거터 8~12.
- **radius**: xs 4 / sm 8 / md 12 / lg 16 / xl 24 / full 999. 예외: 체키 프레임 2(실물 모서리), 티켓 노치 반경 10.
- **elevation** (2단): level0 = 그림자 없음+보더 / level1 = 카드, y2 blur8 ink.900 8% / level2 = 바텀시트·다이얼로그, y8 blur24 ink.900 12%.
- **motion**: short 120ms(칩·토글), standard 200ms(버튼·전환), medium 300ms(카드 전개·바텀시트), long 450ms(체키 획득·스탬프 채움 연출). easing: standard cubic-bezier(0.2,0,0,1) / celebrate cubic-bezier(0.05,0.7,0.1,1).

## 5. motif — 레트로 모티프 시스템 (일러스트 대체)

| 모티프 | 스펙 | 구현 |
|---|---|---|
| 체키 프레임 | 외형 54:86, 이미지 46:62, 하단 여백 비중 20/86 (instax mini 실측) | 비율 Padding 컴포넌트, 패키지 불필요 |
| 티켓 절취선 | 노치 반경 10 + 점선 디바이더 | ticketcher 패키지 또는 CustomClipper+dashPath |
| 우표 테두리 | 스캘럽(천공) 보더 | borders 패키지 StampBorder |
| 스탬프 | 더블 보더 + 미세 회전(-3~3°) + 텍스처 마스크 | ShaderMask + BlendMode.multiply |
| 스탬프 카드 | 기본 8칸(7~10 최적 구간), 빈 칸=점선 원, 마지막 칸=리워드 차별화 | design_system 위젯 |
| 진행 도넛 | 등급 진행 표시 (일본 회원증 3종 세트) | CustomPainter |

- 회원증 카드 = PassKit storeCard 5층 구조(로고 / 스트립 색면 / 주필드 1 / 보조필드 ≤4 / QR) + 등급별 파스텔 스킨.
- QR 표시 화면: 자동 휘도 상승 + 오프라인 캐시 (references 채택 #7).

## 미해결 (Figma 단계로 이월)

- 파스텔 6 hue 전 조합 콘트라스트 실측 검수 및 hex 미세 조정
- serif-formal 한글 폰트 선정
- 등급별 카드 스킨 시안 (어두워지지 않는 위계 — 우표 색/프레임 장식 차등)
- 캐스트 컬러 → hue 슬롯 배정 규칙 (캐스트 확정 인원 의존, PRD 열린 사항)
