---
title: Assen Platform 개발 제약사항
date: 2026-06-11
status: 기준
owner: Assen Entertainment
tags: [Engineering, Constraints, Harness, Flutter, Django, IAP]
related:
  - "[[Development_Constraints]]"
  - "[[LLM_Harness_Index]]"
  - "[[Assen_Platform_Technical_Architecture]]"
  - "[[agent-harness-discourse]]"
  - "[[stack-and-domain-constraints]]"
---

# Assen Platform 개발 제약사항

> ⚠️ **방향 전환 주(2026-07-02):** 2026-06-30 재편으로 현행 제품=범용·서브컬쳐 크리에이터-팬 플랫폼(웹=**React+Next.js** `web/`, 모바일=Flutter — 정본 `Company-OS/02_Product/SDLC/08·09·10`). 본 문서의 **Flutter-web 전제 항목(#11~13)과 메이드/하츠코이·구 수익모델 서술은 구방향 기준**이라 재검토 대상이다. 인간 게이트 원칙(#24~27: 마이그레이션·결제·인증·시크릿·프로덕션)과 하네스 제약은 신방향에도 그대로 유효.

## 문서 목적

Assen Platform(하츠코이 오프라인 경험의 온라인 확장, Flutter web+iOS+Android + Django) 개발의 제약사항을 정의한다. *(구방향 서술)* 이 문서는 Company-OS의 `Development_Constraints`, `LLM_Harness_Index`, `GitOps_Harness`를 **상속**하며 충돌 시 Company-OS 기준 문서가 우선한다. 근거 출처는 `docs/research/` 두 문서에 있다.

핵심 합의 3줄 (하네스 담론 조사):
1. 에이전트에게 기계 판정 가능한 검증 루프를 주되, 작성자가 채점하지 못하게 한다.
2. 규칙 파일은 짧게·사건 기반으로. 강제는 자연어가 아닌 인프라(hook/CI/권한)로.
3. 비가역 영역(마이그레이션·결제·인증·시크릿·프로덕션)은 권한 설계 차원에서 인간 게이트. "자연어 지시는 보안 경계가 아니다."

## 1. 사업·정책 제약 (IAP — 기획 좌우)

1. 한국 iOS 앱 안에서 웹 결제 링크·유도·가격 비교 노출 금지. Epic 판결의 외부 링크 허용은 미국 스토어프런트 한정.
2. 결제 이중 트랙: 웹(토스페이먼츠 빌링) = 정가 주력 채널, 앱 IAP = 수수료 반영 가격 병행 판매. 웹 구매분 앱 소비는 합법(3.1.3(b))이되 동일 상품 IAP 병행 판매가 조건. (버블 2025-07·위버스 검증 패턴)
3. "Reader 앱"(IAP 없는 소비 전용 앱) 전략 금지 — 팬 멤버십+유료 메시지는 reader 카테고리 미해당.
4. 가격 모델은 처음부터 "웹 기준가 + 플랫폼별 마크업" 구조(가격 테이블에 채널 차원 분리). Epic-Google 합의 한국 적용(2026년 말 예정) 시 코드 변경 없이 채널별 재조정 가능해야 한다.
5. 한국 제3자 결제(전기통신사업법 경로)를 수익 모델로 계획하지 않는다 — Apple 26%+별도 바이너리, Google −4%p로 실익 없음.
6. 웹 결제 안내는 앱 외부 채널(이메일, 카카오 채널, 오프라인 매장 POP)로 한다.
7. 콘텐츠 수위는 App Store 1.1.4 기준으로 비성인 유지를 명문화한다.

## 2. 한국 컴플라이언스

8. 가입 또는 첫 결제 시 휴대폰 본인인증 의무화 + 약관 미성년자 조항 + "서류 확인 후 1회 한정 취소" 정책 (민법 제5조 방어).
9. 구독 컴플라이언스 3종 출시 전 완료: 통신판매업 신고 / 청약철회 불가 사전 고지+체험 제공 / 자동결제 30일 사전 동의·해지 고지 플로우 (2025-02 시행 다크패턴 규제).
10. 정기결제는 빌링키 + 자체 스케줄러(Celery Beat). PG 자동결제 심사·계약을 개발 일정에 선행 배치. 초기 PortOne 경유 검토.

## 3. 아키텍처 결정

11. 웹 2-stack: SEO 필요 표면(랜딩·소개·매장 안내)은 기존 HTML 스택(assen-landing) 유지, Flutter web은 로그인 후 앱 경험(PWA) 전용.
12. Flutter web을 콘텐츠/마케팅 페이지에 쓰지 않는다 (1~2MB 초기 페이로드 + 인덱싱 불가).
13. 한국어 입력 폼은 Flutter web 약점으로 전제, IME 회귀 QA를 릴리스 체크리스트에 고정. 크리티컬 입력(결제·가입)은 HTML 표면 분리 검토.
14. Django 5.2 LTS + Django Ninja (타입 힌트=기계 검증 계약, async, OpenAPI 자동). → ADR-0001
15. 스키마 우선 계약: openapi.json 스냅샷 커밋 → CI에서 oasdiff(breaking 차단) + schemathesis(conformance) → swagger_parser로 Dart 클라이언트 생성. 스펙에서 oneOf/anyOf 회피.
16. "메시지"는 채팅이 아니라 피드: DB 레코드 + REST + FCM으로 시작, SSE → WebSocket(Channels)은 필요 입증 후 승급. 외부 채팅 SaaS는 MAU 과금으로 보류.
17. 모노레포: Dart pub workspaces + Melos 7, `apps/` + `packages/`(api_client, design_system, feature 패키지).
18. 오프라인 방문 인증은 결제 연동 적립(@home cafe/스타벅스 모델) 1순위, QR 필요 시 서버 발급 회전 QR(15~60초)만. 정적 QR 금지. @home cafe 앱을 기능 벤치마크로.

## 4. 에이전트 하네스 제약

### 검증 루프
19. 모든 에이전트 태스크에 기계 판정 가능한 완료 기준: Flutter `flutter analyze && flutter test`, Django `ruff check && mypy && pytest` pass가 "done". 체크 없는 태스크는 시작하지 않는다.
20. 개별 테스트 고속 실행 명령을 AGENTS.md에 명시 (`pytest path::test_name`, `flutter test test/foo_test.dart`) — 루프 속도가 곧 품질.
21. 테스트 스위트 상시 green이 최우선 규칙. 깨진 테스트는 에이전트 피드백 루프 전체를 오염시킨다.
22. 작성자≠검토자: 구현 세션의 자체 승인 금지. fresh context 리뷰 또는 "Grill me on these changes / Prove to me this works" 반박 패스.
23. 성공 주장이 아닌 증거 제출: 테스트 출력, 빌드 로그, UI 변경은 스크린샷(기존 playwright shot.mjs 패턴을 Flutter web에 적용).
24. CI 최종 게이트: lint + typecheck + test + Flutter 3타겟 빌드 스모크. 에이전트 PR도 사람 PR과 동일 게이트, 예외 없음.

### 금지·승인 영역
25. Django migrations: `makemigrations`까지 허용, `migrate`(스테이징 이상)와 migrations 파일 직접 수정은 인간 승인. hook으로 migrations 디렉토리 쓰기 차단. django-linear-migrations로 선형 강제.
26. 결제·과금, 인증/권한(authn/authz), 세션/토큰 코드 변경은 인간 리뷰 라벨 강제 (HITL).
27. 시크릿 비접근: `.env`·프로덕션 크레덴셜은 에이전트 읽기 범위에서 deny. 한도 있는 테스트/스테이징 크레덴셜만. gitleaks pre-commit 강제 (AI 커밋 시크릿 유출률 2배).
28. 파괴적 셸 명령(`rm -rf`, `git push --force`, `drop`, `flush`)은 allowlist 밖 → 수동 승인.
29. YOLO/auto 모드는 샌드박스에서만 (신뢰 호스트 네트워크 제한 + 컨테이너/워크트리). lethal trifecta 세 다리(사적 데이터+외부 콘텐츠+외부 통신)가 동시 성립하지 않게.
30. 프로덕션 인프라(배포, DNS, 스토어 릴리즈, 콘솔) 권한을 에이전트에게 부여하지 않는다.
31. 에이전트에게 `--update-goldens`·마이그레이션 수정·테스트 수정을 자율 허용하지 않는다. 골든은 alchemist CI 모드 + 인간 승인, 테스트 약화는 reward hacking 실패 모드(테스트 read-only 완화책).
32. `*.g.dart`/`*.freezed.dart` 등 생성 파일 직접 편집 금지 — build_runner 재실행. hook으로 쓰기 차단.

### 컨텍스트 규율
33. 루트 AGENTS.md 200줄 이하, "코드를 읽어서 알 수 있는 것"은 쓰지 않는다. 매 줄 "지우면 실수하는가?" 테스트.
34. 중첩 배치: `apps/`(Flutter), `server/`(Django)에 각각 AGENTS.md — 가까운 파일 우선으로 스택별 분리.
35. 규칙 파일의 모든 줄은 실제 사건 기반: 같은 실수 2회 반복 시 추가, 정기 가지치기. 사변적 규칙 선제 작성 금지. (LLM_Mistake_Ledger 연동)
36. 권고는 md, 강제는 hook/CI: 포맷터, 시크릿 스캔, migrations·생성파일 차단은 md에 쓰지 말고 hook으로 구현.
37. 검증 가능한 구체 지시만: "깔끔하게" ✗ → "dart format 통과, ruff 규칙 준수" ✓.

### 코드 구조
38. 파일·모듈 작게, 인터페이스 단순하게: Flutter는 feature 단위 디렉토리 + 작은 위젯 파일, Django는 좁은 app 경계. 깊은 모듈 + 동작을 잠그는 테스트.
39. 타입 최대화 = 센서 증설: Dart strict 모드(strict-casts, strict-inference), Python mypy + Pydantic 스키마.
40. 프레임워크 관례를 따르고 독창적 구조 금지: 표준 Django 레이아웃, 통상적 Flutter 패턴. 의존성 버전 명시로 deprecated API 환각 감소 (특히 Riverpod 3.x 명시 — 2.x 문법 환각 빈발).

### 작업 방식
41. 태스크 스코핑: 계획 먼저 → 작은 점진적 diff → 같은 문제 2회 교정 실패 시 컨텍스트 버리고 재시작 → 사람 3시간 이내 단위로 위임 + 명시적 완료 기준. "100줄이면 될 것을 1000줄로" 쓰면 단순화 요구. 최종 정확성의 책임은 인간에게.

## Company-OS 상속 (재확인)

- P0는 Fan CRM이다. 팬덤 수익화(P1/P2: 팬레터, 디지털 체키, 멤버십, 유료 메시지)는 feature flag off로 시작하고 안전/신고/차단보다 먼저 나가지 않는다.
- 가격, 정산, 개인정보 처리방침 문구, 캐스트 동의, 오픈일은 개발 단독 확정 불가 — 승인 필요 항목으로 분리.
- AI 실수는 발견 즉시 `LLM_Mistake_Ledger`에 기록하고 hook/CI 강화로 환류한다.
- PR마다 garbage collection (죽은 코드, 위험 mock, AI-slop 청소).

## 확인 필요 (기획 변수)

| 항목 | 시점 |
|---|---|
| Epic-Google 합의 한국 적용 세부 (수수료 구조 최대 변수) | 2026년 말 시행 시 |
| Apple 대법원 상고 결과 | 2026-06-25 전후 |
| django-ninja OpenAPI 출력 버전 (3.0/3.1) | 코드젠 도구 선정 전 실측 |
| Flutter web 한국어 IME 이슈 현황 | scaffold 후 실측 |
