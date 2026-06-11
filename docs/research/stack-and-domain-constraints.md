---
title: Flutter+Django 팬 플랫폼 기술·도메인 조사
date: 2026-06-11
status: 리서치
owner: Assen Entertainment
tags: [Research, Flutter, Django, IAP, Payments, FanPlatform]
related:
  - "[[CONSTRAINTS]]"
  - "[[Assen_Passport_Technical_Architecture]]"
---

# Flutter + Django 팬 플랫폼 기술 조사

조사일: 2026-06-11. 신뢰도: ●높음(1차 출처 직접 확인) / ◐중간 / ○확인 필요.

## 1. Flutter 크로스플랫폼 (web 포함)

### Flutter web의 한계
- **SEO 공식 부적합** ●: 공식 FAQ가 "출력이 검색엔진 인덱싱 요구와 맞지 않는다"고 명시, 마케팅/콘텐츠 페이지는 별도 HTML 권고. (docs.flutter.dev/platform-integration/web/faq)
- **렌더러/초기 로딩** ●: HTML 렌더러는 3.29(2025-02)에서 제거. CanvasKit(~1.5MB)/skwasm(~1.1MB)만 남음 → 첫 페인트 전 1~2MB+가 구조적 하한. 로그인 후 앱 경험엔 수용 가능.
- **한국어 IME** ●: 한글 조합 깨짐(#138288), 빠른 입력 시 오류(#126247) 등 일관된 약점. 한국어 입력 폼 별도 QA 필수. (현재 open/closed 상태 ○)
- **웹뷰** ●: web 타깃은 iframe 기반 — 임의 JS 불가, CSP에 막히면 임베드 불가.
- **2025 릴리스** ●: 3.32(웹 hot reload 실험) → 3.35(기본) → 3.38(2025-11 stable). wasm은 프로덕션 가능하나 기본값 아님(○).

### 아키텍처 권고
- 공식: MVVM "strongly recommend" + 리포지터리 패턴. Flutter web은 "앱 중심 경험(PWA/SPA)" 전용. (docs.flutter.dev/app-architecture)
- 상태관리: 사실상 표준 Riverpod — **3.0이 2025-09 출시**(현재 3.3.x). 2.x→3.x 문법 차이가 커서 에이전트의 구버전 문법 환각 빈발 지점. (riverpod.dev/docs/whats_new)
- 모노레포: Dart 3.6+ pub workspaces 네이티브 + Melos 7(스크립트·버저닝). (dart.dev/tools/pub/workspaces)

## 2. Django 백엔드

- **DRF**: 3.16(2025-03) 유지되나 maintenance mode 논의 공개적 존재. async 미지원. OpenAPI는 drf-spectacular + 수동 보정.
- **Django Ninja** ●: 1.6.x, 타입 힌트+Pydantic v2, async 내장, OpenAPI 자동. 함수 시그니처 = 기계 검증 계약 → 에이전트 친화성 우위. 리스크: 단일 메인테이너 중심(◐). (django-ninja.dev)
- **Django 버전** ●: 5.2 LTS(2028-04까지 지원). 6.0의 내장 Tasks는 인터페이스 수준 — Celery 대체 아님(DEP 14).
- **코드젠 파이프라인**: ninja `/api/openapi.json` → swagger_parser(retrofit+freezed, 1순위) 또는 openapi-generator dart-dio(nullable 버그 이력 ◐). 함정: oneOf/anyOf 다형 응답에 Dart 생성기 전반 취약 → 스펙에서 회피. ninja의 OpenAPI 출력 버전(3.0/3.1)은 실측 필요(○).
- **실시간**: 버블류는 1:N 브로드캐스트 + 팬 답장은 아티스트만 봄 = read-heavy 단방향. DB 레코드 + REST 피드 + FCM으로 시작, SSE → WebSocket(Channels 4.3.x)은 필요 입증 후 승급. Sendbird/Stream은 MAU 과금 부담(◐).
- **Celery** ●: 5.6.x 표준. 결제/구독 갱신 배치는 Celery + Redis + Beat.

## 3. 팬 플랫폼 도메인 제약 (기획 좌우)

### iOS/Android 인앱결제
- **Apple 3.1.1** ●: 디지털 기능 해제(멤버십/유료 메시지/독점 콘텐츠)는 IAP 의무. 30%, Small Business(연 $1M 이하) 15%, 자동갱신 구독 2년차~ 15%. (developer.apple.com/app-store/review/guidelines/)
- **미국 한정 예외** ●: Epic v. Apple(2025-04) 이후 미국 스토어프런트만 외부 결제 링크 자유(현재 0%, 항소심이 비용 기반 수수료 허용으로 환송 — 잠정적). **한국 iOS 앱 내 웹 결제 유도/링크는 여전히 금지.**
- **한국 전기통신사업법** ●: 제3자 결제 합법이나 Apple 26%(+한국 전용 바이너리) / Google −4%p → PG 수수료 더하면 실익 없음. (developer.apple.com/support/storekit-external-entitlement-kr/)
- **Google Play** ●: 디지털 상품 Play Billing 의무. 연 $1M까지 15% / 초과 30% / 자동갱신 구독 일괄 15%. 1:1 비녹화 개인 서비스 예외는 1:N 메시지 미해당. (support.google.com/googleplay/android-developer/answer/10281818)
- **Epic-Google 합의(2026-03)** ◐: 신규 설치 IAP 20%(프로그램 15%), 구독 10%, 외부 웹 결제 유도 허용 — 한국 적용 2026-12-31까지 롤아웃 예정(○ 시행 시 재확인. 사업계획 최대 변수).
- **검증된 우회 패턴** ●:
  - "웹 구매 + 앱 소비" 합법(3.1.3(b) Multiplatform Services). 조건: 앱 내 웹 결제 유도 금지(미국 외) + **동일 상품 IAP 병행 판매**.
  - Reader 앱(3.1.3(a))은 잡지·도서·오디오·음악·비디오 한정 — 팬 멤버십+유료 메시지 미해당.
  - **DearU Bubble**: 2025-07 앱 가격 인상(4,500→5,000원) + 웹스토어(4,500원) = 이중 가격. **Weverse**: Jelly 웹 구매 보너스 최대 10%. **Patreon**: 2024-11 iOS IAP 강제 적용.
  - 이메일/카카오 채널 등 앱 외부 채널에서 웹 결제 안내는 자유.
- **성인 콘텐츠** ●: App Store 1.1.4 포르노 금지(OnlyFans 앱 부재 이유). 비성인 유지 시 표준 IAP 경로 문제 없음.

### 한국 PG·본인인증·미성년자
- **정기결제** ●: 토스페이먼츠 빌링 — 카드 등록 → 빌링키 → 서버 자동 승인. 스케줄러 미제공(자체 Celery Beat) + 자동결제 별도 심사·계약. 간편결제는 자동결제 미지원. PortOne 경유 시 PG 교체 유연성. (docs.tosspayments.com/guides/v2/billing)
- **본인인증** ●: PASS 건당 약 30~50원. 성인인증 의무는 청소년유해매체물 한정이나, 미성년자 결제 방어용 도입이 실무 표준.
- **미성년자 결제 취소** ●: 민법 제5조 — 법정대리인 동의 없는 결제 취소 가능. 완화: 가입 본인인증 + 약관 명시 + 1회 한정 취소 정책.
- **구독 컴플라이언스 3종** ●: ①통신판매업 신고 ②디지털콘텐츠 청약철회 7일(제공 개시 시 불가 — 사전 고지+체험) ③2025-02 시행 다크패턴 규제(전환·증액 30일 전 동의 + 해지 고지).

### 오프라인 연계
- **@home cafe 공식 앱(최직접 벤치마크)** ●: 회원증·등급, 방문 기록(날짜·담당 메이드·체키 촬영 메이드), Collectible CHEKI 디지털 수집, 결제 시점 포인트·등급 갱신. (maidcafe-athome.com/mobile-app)
- 체키 디지털화: instax UP!(실물 스캔), Favsquad(이미지 배포 → 팬이 instax 인쇄).
- 방문 인증 ◐: 정적 QR은 스크린샷으로 뚫림. ①결제 연동 적립(스타벅스 모델) 1순위 ②서버 발급 회전 QR(15~60초, Google Wallet Rotating Barcodes 레퍼런스).

## 4. AI 에이전트 주도 개발 (스택 특화)

- Flutter 테스트 ●: golden_toolkit discontinued → **alchemist**(CI 모드가 텍스트를 사각형으로 대체해 폰트 flake 구조적 제거 — Docker만으론 불충분 #131559). `--update-goldens`는 인간 게이트 필요. 린트 very_good_analysis. e2e는 patrol(네이티브 다이얼로그 필요 시만). **공식 Flutter AI rules 템플릿**: docs.flutter.dev/ai/ai-rules
- API 계약 테스트 ●: 스펙 스냅샷 커밋 → CI에서 oasdiff(breaking 감지) + schemathesis(ASGI 인프로세스 conformance). 단일 팀 소유면 Pact는 과투자.
- Django ●: pytest-django + factory_boy(JSON fixture 비권장), `makemigrations --check` CI 게이트, **django-linear-migrations**(병렬 에이전트의 마이그레이션 충돌을 git 컨플릭트로 조기 표면화), docker compose(postgres+redis) + django-environ.
- 에이전트가 자주 망가뜨리는 것 ●/◐: ①구버전 API 환각(Riverpod 2 vs 3) ②`*.g.dart`/`*.freezed.dart` 직접 편집 ③테스트 약화/reward hacking(arXiv 2511.18397 — 테스트 read-only가 효과적 완화) ④마이그레이션 충돌 ⑤`--update-goldens` 남용.

## 확인 필요 잔여 항목

- Epic-Google 합의 한국 적용 세부 (2026년 말 시행 시 재확인 — 최대 변수)
- Apple 대법원 상고 결과 (2026-06-25 전후)
- django-ninja OpenAPI 출력 버전 (3.0/3.1 실측)
- Flutter web 한국어 IME 이슈 open/closed 현황
- 청소년보호책임자 지정 시행령 수치 기준
- 위버스 QR 회전 방식 세부

→ 적용 제약은 [[CONSTRAINTS]] 1~3장에 반영.
