# 잔여 게이트 정리 — 대표 배포범위 100% 커버리지 (2026-07-17)

> 목적: 대표가 요구한 **소프트런치 배포범위 100% 완성도**( = 실 PG 결제 + 실 19+ 본인인증
> 두 외부 게이트만 mock/fail-closed, 나머지 전 기능 실구현)를 달성하기 위해 **무엇이 남았는지**를
> 정리한다. 내일 작업 재개용 핸드오프.
>
> 원천: `mvp-release-boundary-2026-07-13.md`(레인 A~E) + `audit-remediation-plan-2026-07-10.md`
> (ASS-284 블로커) + 인증 재설계(PR #157~161) + Codex 감사 프로그램(PR #147~156).
> 각 항목의 현재 코드 상태는 2026-07-17 검증.

---

## 0. 오늘까지 완료 (검증됨)

- **인증 재설계 A→C 전체 완료** (PR #157~161, dev 6992a98, AWS dev 라이브 검증):
  로그인 = 소셜(kakao/google/naver) + 이메일/PW(확인메일 필수), 폰 OTP 완전 제거.
  가입 자유·열람 자유, 상호작용/구매는 본인인증(mock) 필수. `/api/fan/login` → 404,
  `/api/fan/login/email` → 200(422 스키마), 소셜 start → 200 확인.
- **Codex 감사 프로그램 16/20** (PR #147~156): OAuth state·체크아웃 멱등·SSR세션·동의캡처·
  탈퇴카피·엔타이틀먼트·미디어·이행FSM·구독빌링·PENDING→PAID·환불역전·리텐션·오프보딩.
- **프로덕션 활성화 블로커(ASS-284) 언게이트 하드닝 — 검증상 완료**:
  - ASS-285 엔트리포인트 prod 강제(dev fallback 제거) ✅
  - ASS-288 seed 가드(`ALLOW_DEMO_SEED` + prod 거부) ✅
  - ASS-290 OpenAPI drift CI 게이트(ci.yml·web-ci.yml) ✅
  - ASS-293 업로드 EXIF/메타데이터 strip + 재인코딩 ✅
  - ASS-295 prod rate-limit 공유 백엔드(redis) 강제 ✅

---

## A. 외부/법무 게이트 — 대표 명시 제외 (코드로 못 닫음 · 결정/계약 대기)

이 범주는 대표가 "제외"라 한 두 외부 게이트 + 법무. **코드는 seam/상태머신까지 완성**돼 있고
실 키·계약·사인만 남는다.

| # | 게이트 | 코드 상태 | 남은 것(외부) |
|---|---|---|---|
| A1 | **실 PG 결제** | 상태머신(PENDING→승인→PAID)·`PaymentAttempt` 원장·환불역전(`PaymentReversal`)·`provenance=external` seam 완성(audit #2/#3/#4) | 포트원 **가맹심사** + 사업자등록·통신판매업 신고 + 운영키 + 캡처/웹훅 실배선(sandbox→real 키 전환) |
| A2 | **실 19+ 본인인증** | mock `verify/start`·`verify/confirm`(adult+kyc 플래그) 완성·웹 게이팅 UX(B2) 완성 | 포트원 본인인증 or PASS/NICE **계약** + 실 verify 연동 |
| A3 | **법무 정책** | 약관/개인정보/환불 페이지 스켈레톤·동의 버저닝(consent/versions) 존재 | 법무 **사인**(청소년보호법·정보통신망법 §42-3/§44-2·n번방방지) + 통신판매중개 면책 문구 확정 |
| A4 | **ASS-286 결제 하드 컨테인먼트** (A1 종속) | ⚠️ `ENABLE_MOCK_PAYMENT` **앱코드 미참조**(설정·테스트만) → `False`일 때 create_order/subscribe/tier변경이 503 반환하지 않음 | 실 PG 활성화 결정 시: `ENABLE_MOCK_PAYMENT=False`→코드화 503(부작용 0) 배선 + false-flag 회귀테스트 |
| A5 | **ASS-287 privacy B** (Privacy Owner 종속) | A-1 배송체크아웃 차단·A-2 폰 HMAC·A-3 주소 DTO 최소화는 진행됨 | 리텐션/삭제 값·배송PII 수집 여부·정책 문구 = 결정권자 대기 |

---

## B. 코드로 닫을 수 있는 잔여 게이트 — 내일 작업 대상 (100% 완성도)

| # | 게이트 | 현재 상태 | 작업 |
|---|---|---|---|
| **B1** | ★★**모바일 인증 파리티 (긴급)** | `apps/assen_mobile` 인증이 **여전히 폰 OTP**(auth_api/auth_controller/dev_otp/login_screen). Wave C에서 서버 폰 엔드포인트 제거 → **모바일 로그인이 현 서버에서 404로 깨짐** | 웹 B1/B2와 동일하게 이메일/소셜 로그인 + 본인인증 KYC 게이팅으로 이관. `login/email`·`signup/email`·`verify-email`·social·verify 배선. otp_field/dev_otp 제거 |
| **B2** | **프로덕션 배포 (레인 D)** | dev는 ECS 배포·라이브. **프로드 미배포**(MVP 바운더리 07-13 "terraform apply 안 됨") | terraform apply·prod env/secret·도메인·SSL. dev와 동일 파이프라인 |
| **B3** | **결제 sandbox 어댑터 (레인 B 코드부)** | provider-agnostic 승인/캡처 경계 seam 존재 | 포트원 **sandbox 키**로 어댑터 선행 구현(심사 완료 시 실 키만 전환) — A1의 코드 선행분 |
| **B4** | **크리에이터/팬 모드 분리 UX (레인 A)** | become-creator(studio_create_profile) 서버·웹 존재·KYC 게이트 적용 | 모드 전환/등록 UX 완성도 점검(웹 완료 여부 확인·모바일은 B1에 포함) |
| **B5** | **인증 재설계 후속** | — | AWS dev 데모계정 재시드(이메일 크리덴셜 backfill)·`web/scripts/integration-smoke.mjs` 삭제(제거 엔드포인트 호출·journey.spec.ts로 대체)·config/*.py 도크스트링 stale 참조 정리·이메일 가입 마케팅동의 단위테스트 |
| **B6** | **디자인 고도화** (릴리즈 블로커 아님) | 브랜드색 #5A4DF0 확정·DS 구현 완비 | 대표 방향 후 디자인 9점대·Pretendard/실이미지 |

---

## C. 감사 미검증 블라인드스팟 (릴리즈 직전 점검)

`audit-remediation-plan §5` — 실 PostgreSQL/Redis 멀티워커·ECS task def·ALB 로그·실 Sentry
transport·S3/CDN·실 Playwright 스택·iOS·GitHub 브랜치보호·외부 결제/KYC/SMS/IAP·Linux 클린클론·
골든 워크플로. Category A/B 착지 후 점검.

---

## 우선순위 제안 (내일)

1. **B1 모바일 인증 파리티** — 현재 모바일 로그인이 깨져 있어 가장 시급(회귀). 웹 B1/B2 패턴 재사용.
2. **B2 프로덕션 배포 + B5 후속 정리** — 소프트런치 인프라 실체화.
3. **B3 포트원 sandbox 어댑터** — A1 결제의 코드 선행분(외부 심사와 병렬).
4. A(외부/법무)는 대표/법무의 계약·사인 진행에 종속 — 코드는 대기 상태로 완비.
