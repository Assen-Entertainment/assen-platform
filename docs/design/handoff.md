---
title: Vite 랜딩 → Flutter 앱 핸드오프 URL 계약
date: 2026-06-12
status: 기준
owner: Assen Entertainment
tags: [Design, Routing, Handoff]
linear: ASS-131
related: ["[[screens]]"]
---

# Vite 랜딩 → Flutter 앱 핸드오프 URL 계약

공개 랜딩(`landing/`, Vite)과 앱(`apps/fan_app`, Flutter web)은 **별도 배포물**이다.
랜딩의 `/`는 Flutter 라우트가 아니며, Flutter web의 진입점은 `/login`이다(plan §4.3).
이 문서는 랜딩 CTA가 Flutter 앱으로 사용자를 넘길 때의 **URL 파라미터 계약**만 고정한다.

> landing/ 디렉토리는 이 트랙에서 **수정하지 않는다**. 현재 랜딩 CTA는 사전 등록
> 폼(`#cta` 앵커)이며 앱 출시 전까지 외부 리다이렉트를 켜지 않는다. 아래 계약은
> 출시 시 랜딩이 채택할 **목표 계약**이고, Flutter 측 수신 상수는 이미 정의해 둔다.

## 1. 리다이렉트 대상

| 출발 (랜딩) | 도착 (Flutter web) | 비고 |
|---|---|---|
| 헤더/히어로 "시작하기"·"로그인" CTA | `/login` | 미인증 기본 진입점 |
| "가입하기" CTA | `/signup` | A2 약관 → A3 본인인증 → A4 닉네임 |

## 2. 쿼리 파라미터 (최소 집합)

전부 **선택적**이며 의미는 표준 관례를 따른다. 앱은 알 수 없는 파라미터를 무시한다.

| 파라미터 | 예시 | 의미 |
|---|---|---|
| `return_to` | `/qr` | 인증 완료 후 복귀할 **앱 내부 경로**. 반드시 `/`로 시작하는 상대 경로만 허용(오픈 리다이렉트 방지 — 외부 URL은 거부하고 `/home`으로 폴백). |
| `utm_source` | `landing` | 유입 출처 (분석용). |
| `utm_medium` | `cta_hero` | 유입 매체/위치. |
| `utm_campaign` | `prelaunch` | 캠페인 식별자. |

예: `https://app.assen.example/login?return_to=/qr&utm_source=landing&utm_medium=cta_hero`

## 3. `return_to` 안전 규칙 (가드 계약)

1. 값이 없거나 비어 있으면 인증 후 `/home`으로 보낸다.
2. **allowlist 파싱**으로만 통과시킨다: 파싱 결과가 스킴 없음 + authority 없음 + path가 `/`로 시작 + `//`로 시작하지 않음. 다음은 전부 **거부** 후 `/home` 폴백 — 오픈 리다이렉트 차단:
   - 스킴-상대(`//host`)·절대 URL·스킴 보유 값(`javascript:` 포함)
   - **백슬래시(`\`)·TAB·LF·CR 포함 값** — 브라우저(WHATWG URL)는 제어문자를 제거하고 `\`를 `/`로 취급하므로 `/\evil.com`·TAB 분절 `//evil.com`이 오프오리진으로 재정규화된다
   - 쿼리/프래그먼트의 콜론(`?t=12:30`)은 정상 경로로 허용 — 판정은 path 컴포넌트 기준
3. 허용된 값은 그대로 `context.go(return_to)` 대상이 된다. 미인증 진입 시 가드가 이 값을 보존했다가 로그인 성공 후 사용한다(예: `/qr` 딥링크 → `/login?return_to=/qr` → 로그인 → `/qr`).

## 4. Flutter 측 단일 출처

수신 상수·파싱은 `apps/fan_app/lib/handoff.dart`의 `LandingHandoff`에 있다
(쿼리 키 이름, `return_to` 검증, 기본 복귀 경로). 라우트 가드는 이 클래스만 참조한다.
