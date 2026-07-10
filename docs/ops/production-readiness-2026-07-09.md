# Assen 프로덕션 준비 고도화 — 종합 (2026-07-09)

> **내부 열람용(insider).** 4개 축(백엔드·웹·모바일·인프라) 근거 기반 조사 결과를 종합한 프로덕션 준비 로드맵.
> Linear 프로젝트: **프로덕션 준비 고도화 (Production-Readiness)** — 이슈 `ASS-261 ~ ASS-283` (23건).
> 조사 방식: 4개 병렬 코드 조사(파일:라인 근거 수집) → 종합·우선순위화.

## 0. 핵심 통찰 (Executive Summary)

**Assen은 규율 있게 "fail-closed 목(mock)"으로 지어진, 경계(boundary)가 훌륭한 뼈대다.**
모든 목은 `base.py`에서 `False`로 하드코딩된 플래그로 게이트되고 `dev/test/demo`에서만 `True` —
즉 prod는 목을 신뢰하는 대신 **503으로 fail-closed**된다. 이는 매우 규율 있는 설계다.
그러나 그 결과, **경계 뒤의 "진짜 구현"이 대부분 미착수**다.

> **고도화 = ① 경계 뒤 실구현 · ② 클라우드/CD · ③ 모바일 기능 폭 · ④ 말단 폴리시**

"목이 있다"는 것 자체는 결함이 아니다. 결함은 목 뒤에 실물이 없다는 것이며,
이 문서는 그 실물을 채우는 작업을 Tier·착수가능성으로 구조화한다.

## 1. 이미 견고한 것 (재작업 불요)

조사에서 각 축이 명시적으로 "이미 잘 됨"으로 확인한 항목 — 신규 작업 대상 아님:

- **멱등성**: 주문(`apps/commerce/models.py:157-175`, `api.py:720-852`)·쿠폰(`apps/coupon/models.py:115-128`) 실제 처리됨.
- **시크릿 fail-closed**: prod `SECRET_KEY`/`ALLOWED_HOSTS` 필수(`prod.py:24-26`).
- **CORS/CSRF prod 차단**(`prod.py:44-50`), 웹 Dockerfile prod-guard(`NEXT_PUBLIC_API_URL` 없이 빌드 거부, `web/Dockerfile:23-28`).
- **모바일 안전 토큰 저장**: Keychain/Keystore 원자적 단일키 JSON, fail-closed(`auth/token_store.dart:49-101`).
- **CI 게이트**: gitleaks·mypy·ruff·pytest·tsc·eslint·번들예산 전부 강제. CODEOWNERS(HITL) 존재.
- **Sentry PII 스크러버**: 서버측 관측성은 견고하게 구축(스크러빙 철저).
- **Pretendard 자체호스팅 완료**(`app/layout.tsx:15`) — 폰트는 미결 아님.
- **모바일 읽기 화면 실배선**(discovery/feed/mypage/orders/store/studio/search/notifications 전부 실 Dio) + **R13/R14 브랜드 표현 사실상 랜딩**(`core_tokens/lib/src/brand.dart`).
- **웹 대부분 플로우 실 API 배선**(`USE_API` 게이트, 목은 라이브 빌드에서 tree-shake).
- **배포 스크립트 인간 게이트**: main-only·clean-tree·CI-green·migrate exit 0·services-stable 확인(`deploy-prod-ecs.sh`).

## 2. Tier 0 — 실런칭 차단 (돈·법·보안·데이터)

| 이슈 | 항목 | 착수 | 핵심 근거 |
|---|---|---|---|
| **ASS-261** | 결제(PG) 실연동 — 토큰화 + 웹훅/정산 대사 | 🔴 PG계약+PCI | `config/payment.py:85,98` · `event_log/events.py:85,121,410`(핸들러 없음) · 웹 `lib/api/index.ts:776,1097` |
| **ASS-262** | 본인인증/성인(19+) KYC 실 제공사 | 🔴 제공사+법무 | `config/identity_verify.py:91-94`(항상 adult=True) · 웹 `age-gate/page.tsx:32-40` |
| **ASS-263** | OTP 실 SMS + Redis 공유상태(F3) | 🟡 Redis🟢/SMS🔴 | `config/otp.py:15-25`(요청마다 fresh sender, 만료·1회성 런타임 미강제) |
| **ASS-264** | 정산/재무 실계산(Studio 정산·분석·대시보드) | 🟡 집계🟢/금액🔴 | `cheki/services.py:15` · 웹 `studio/settlement/page.tsx:40`·`lib/studio-mock.ts:104-137` |
| **ASS-265** | prod 설정 fail-open 폐쇄(DATABASE_URL) | 🟢 **now** | `base.py:225-230`(prod.py 미오버라이드 → `assen:assen@localhost` 조용히 상속) |
| **ASS-266** | #25 마이그레이션 정식 전환 | 🟢 **now** | `base.py:121,128,132`·`deploy-prod-ecs.sh:70-74`·`Dockerfile:36`(migrate 미실행) |

## 3. Tier 1 — 실트래픽 전 필수 (인프라·공유상태·전달·관측)

| 이슈 | 항목 | 착수 | 핵심 근거 |
|---|---|---|---|
| **ASS-267** | 클라우드 IaC + CD 파이프라인 | 🔴 클라우드계정/E10 | IaC 0(Terraform/k8s 없음) · `deploy-prod-ecs.sh:15-35`(env var 이름만) |
| **ASS-268** | Redis 공유 인프라 + celery worker/beat | 🟢 **now(dev)** | `ratelimit.py:76`·`base.py:71-75,187-221`·`Dockerfile:36`(daphne만) · `docker-compose.yml:38`(WSGI override) |
| **ASS-269** | 알림 실발송(FCM/APNs·email·SMS) | 🔴 발송사 | `notification/adapters.py:3`(mock만, 어디로도 미발송) |
| **ASS-270** | 관측성 완성(웹 Sentry·메트릭·알럿·/readyz) | 🟡 웹Sentry🟢 | 웹 `@sentry` 0 · `observability.py:339-351`(DSN 없으면 no-op) · `/readyz` ALB 미배선 |
| **ASS-271** | 업로드 실화(S3/CDN·모더레이션·Pillow) ⭐디자인9점 선행 | 🔴 S3/CDN | `uploads/api.py:78-89`(전부 통과) · `base.py:284-294`(64B 스니핑) |
| **ASS-272** | DB 백업/PITR 전략 | 🔴 RDS | `adr/0003-hosting-aws.md:20`(TBD) · `docker-compose.yml:88-89`(bare 볼륨) |

## 4. Tier 2 — 성숙도·폴리시·품질

| 이슈 | 항목 | 착수 | 핵심 근거 |
|---|---|---|---|
| **ASS-273** | 검색 고도화(Postgres 풀텍스트/GIN) | 🟢 **now** | `creator/api.py:210-232`(icontains, 상한10, 페이지네이션 없음) |
| **ASS-274** | 추천 로직 실화 | 🟢 **now(기초)** | 웹 `discovery-view.tsx:82-84,168-171`(팔로워순·reverse·동일리스트) |
| **ASS-275** | 웹 말단 UX(SSR-only 뷰 에러상태·스켈레톤) | 🟢 **now** | `orders-view.tsx`·`subscriptions-view.tsx:25-26`·`notifications-view.tsx`(isError 없음) |
| **ASS-276** | dev 라우트 noindex(/gallery·/design-system) | 🟢 **now** | `gallery/page.tsx:19` · `robots.ts:6`(checkout·api만 disallow) |
| **ASS-277** | i18n 레이어 도입 | 🟢 now(대작업) | `layout.tsx:26`(ko_KR 하드코딩) |
| **ASS-278** | 보안 헤더 CSP(report-only→enforce) | 🟢 now(신중) | `middleware.py:63,73-75`(CSP 보류) · `prod.py:38-40`(HSTS 1h) |
| **ASS-279** | CI 게이트 보강(비주얼·커버리지·SAST) | 🟢 **now** | `e2e.yml:15-16`·`web-ci.yml:34`·`ci.yml:79-82` · CodeQL/Dependabot 없음 |
| **ASS-280** | 모바일 커머스 스파인(checkout·IAP·주문) | 🔴 IAP/PG | `store/product_screen.dart:21-22`·`pubspec.yaml`(in_app_purchase 없음) |
| **ASS-281** | 모바일 Studio 저작 도구(image_picker) | 🟡 업로드 후행 | `studio/studio_screen.dart:12-20`(stat만) · `pubspec.yaml:28` |
| **ASS-282** | 모바일 네이티브(push·딥링크·다크모드) | 🟡 다크모드🟢 | `app/app.dart:23-26`(ThemeMode.light 고정, darkTheme=light) |
| **ASS-283** | 리포 위생(dev 아티팩트·stale docstring) | 🟢 **now** | `server/dev.sqlite3`·`celerybeat-schedule`·docstring 8곳 |

## 5. 착수 가능성 구분 (의사결정용)

| 🟢 지금 착수 가능 (외부계약 불요) | 🔴 대표/법무/외부계약 선행 |
|---|---|
| ASS-265 prod fail-close, ASS-266 마이그레이션, ASS-268 Redis/celery(dev), ASS-270 웹Sentry, ASS-273 검색, ASS-274 추천, ASS-275 웹말단, ASS-276 noindex, ASS-277 i18n, ASS-278 CSP, ASS-279 CI, ASS-283 위생, ASS-282 다크모드 | ASS-261 PG(PCI), ASS-262 KYC, ASS-263 실SMS, ASS-267 클라우드(E10), ASS-269 FCM/APNs, ASS-271 S3/CDN, ASS-272 RDS, ASS-280 IAP |

## 6. 가장 큰 레버 3

1. **돈+신원 신뢰 루프 폐쇄** (ASS-261·262·264) — 실 PG(웹훅/대사) + 실 KYC + 실 정산.
   "데모 ↔ 합법 결제 플랫폼"의 경계. 커머스·멤버십·환불·정산 전 표면을 한 번에 해제.
2. **공유상태 인프라(Redis) 일괄 실화** (ASS-268·263·270) — 레이트리밋·Channels·OTP상태·celery
   동시 정상화(멀티태스크 정합 + 유일한 런타임-불안전 목 F3 해소).
3. **클라우드 IaC/CD + fail-open 폐쇄** (ASS-267·265·266·272) —
   "prod-parity-local → 실 production" 전환.

## 7. 착수 배치 (이번 세션, 🟢 항목 중)

`feature/prod-parity-env` 브랜치. 외부계약 불요·저위험·검증가능 항목 우선:

- **ASS-265** prod 설정 fail-open 폐쇄 (DATABASE_URL/REDIS 미설정 시 부팅 차단)
- **ASS-266** #25 마이그레이션 정식 전환 (stale docstring/문서 정정, 배포 migrate 배선)
- **ASS-268** Redis 공유상태 + celery worker/beat (dev/compose)
- **ASS-270**(부분) 웹 Sentry 배선
- **ASS-275** 웹 말단 UX (SSR-only 뷰 에러상태)
- **ASS-276** dev 라우트 noindex
- **ASS-283** 리포 위생 (dev 아티팩트 제거)
- **ASS-273**(여건 시) 검색 고도화

각 착수 결과는 커밋 메시지 + 본 문서 §7 하위에 갱신 기록.

---
_출처: 2026-07-09 4축 병렬 조사. 갱신 시 Linear 이슈 상태와 동기화._
