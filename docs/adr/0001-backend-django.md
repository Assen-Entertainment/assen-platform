# ADR-0001: 백엔드 프레임워크를 Django로 확정

- 날짜: 2026-06-11
- 상태: Accepted
- 결정자: 대표 (Geon Yong Kim)

## 맥락

Company-OS의 `Assen_Platform_Technical_Architecture.md`(2026-06-10 작성, 당시 명칭 Assen_Passport_Technical_Architecture — ASS-89로 개명)는 백엔드를 "TypeScript modular monolith API를 기본 후보"로 두되 "최종 framework는 구현 repo scaffold 시 ADR로 고정"하도록 위임했다. 본 ADR이 그 결정이다.

## 결정

**Django 5.2 LTS + Django Ninja**를 백엔드로 확정한다.

- Django 5.2 LTS: 2028-04까지 보안 지원. ORM·admin·auth·migrations가 Fan CRM(P0)의 운영 원장 + 운영자 콘솔 요구와 일치.
- Django Ninja: 타입 힌트 + Pydantic v2 기반 → 함수 시그니처가 기계 검증 가능한 API 계약이 되어 OpenAPI 자동 생성·Flutter 코드젠 파이프라인(CONSTRAINTS #15)과 에이전트 주도 개발(타입체커 = 하네스 센서)에 유리. async 내장.
- 비동기 작업: Celery + Redis + Beat (Django 6.0 내장 Tasks는 인터페이스 수준이라 대체 불가).

## 대안 검토

- **TypeScript modular monolith (기존 후보)**: 프론트(Dart)와 어차피 언어 불일치. Django 대비 운영 원장(ORM/migrations/admin) 성숙도에서 열위. 채택 안 함.
- **DRF**: 생태계는 크지만 maintenance mode 논의, async 미지원, OpenAPI에 drf-spectacular 수동 보정 필요. Ninja 대비 에이전트 친화성 열위. 채택 안 함.

## 결과

- 기존 아키텍처 문서의 나머지 결정(PostgreSQL + append-only event_log, REST/OpenAPI 우선, staged identity, feature flag 등)은 그대로 유효하다.
- Company-OS `Assen_Platform_Technical_Architecture.md`의 Backend 행을 본 ADR 참조로 갱신했다 (2026-06-11, ASS-80 완료. 문서 개명은 ASS-89).
- 리스크: Django Ninja는 단일 메인테이너 중심 — 심각한 정체 시 DRF+drf-spectacular로 회귀 가능하도록 뷰 로직과 스키마를 분리해 둔다.
- 근거 상세: `docs/research/stack-and-domain-constraints.md` 2장.
