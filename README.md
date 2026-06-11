# Assen Platform

메이드카페 '하츠코이'의 오프라인 경험을 온라인으로 잇는 크로스플랫폼 서비스.
오프라인 방문(Fan CRM)을 기록·연결하는 것이 P0이며, 이후 Likey/Bubble류 온라인 활동(멤버십·메시지·디지털 체키)으로 확장한다.

- 프론트엔드: Flutter (web + iOS + Android) — web은 로그인 후 앱 경험 전용 (SEO 표면은 assen-landing)
- 백엔드: Django 5.2 LTS + Django Ninja (ADR-0001)
- 태스크 추적: Linear — 팀 ASS, 프로젝트 "Assen Platform"

## 구조

| 경로 | 내용 |
|---|---|
| `apps/` | Flutter 앱 — `fan_app`(팬+캐스트), `operator_app`(운영자/관리자) |
| `packages/` | 공유 패키지 — core_tokens · ui_kit · api_client · features · operator_features · test_fixtures |
| `server/` | Django 5.2 + Ninja 백엔드 (도메인 앱 17개, uv 관리) |
| `landing/` | 공개 랜딩 (Vite + GSAP — SEO 표면, Flutter 아님) |
| `docker-compose.yml` | 로컬/CI 개발 스택 (postgres · redis · api · celery worker/beat) |
| `.github/workflows/ci.yml` | CI 게이트 — lint/typecheck/test/빌드 스모크/compose/gitleaks |

## 문서

| 문서 | 내용 |
|---|---|
| `AGENTS.md` | 에이전트 하네스 (필수 선행 문서, 검증 계약, GitOps, 금지 영역) |
| `apps/AGENTS.md` · `server/AGENTS.md` | 스택별 중첩 하네스 |
| `docs/CONSTRAINTS.md` | 개발 제약사항 41개 (기준 문서) |
| `docs/adr/` | 아키텍처 결정 기록 |
| `docs/research/` | 제약의 근거 리서치 (하네스 담론, 스택·IAP·컴플라이언스) |

작업 전 `AGENTS.md`(검증 계약·GitOps)와 `docs/CONSTRAINTS.md`를 읽을 것.
