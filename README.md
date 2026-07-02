# Assen Platform

> ⚠️ **방향 전환(2026-06-30):** 범용·서브컬쳐 **크리에이터-팬 플랫폼**으로 재편 — 신방향 정본은 `Company-OS/02_Product/SDLC/08·09·10`. 웹=**React+Next.js**(`web/`), 모바일=Flutter, 백엔드=Django Ninja(신규 도메인 5앱). 아래 메이드카페(하츠코이) 서술·백로그는 구방향 기록이며 순차 아카이브(B9/M10) 대상이다.

메이드카페 '하츠코이'의 오프라인 경험을 온라인으로 잇는 크로스플랫폼 서비스. *(구방향)*
오프라인 방문(Fan CRM)을 기록·연결하는 것이 P0이며, 이후 Likey/Bubble류 온라인 활동(멤버십·메시지·디지털 체키)으로 확장한다.

- 웹: **React + Next.js + TS + Tailwind v4** (`web/`, ADR-09/10) — 신방향
- 모바일: Flutter (iOS + Android; 구 Flutter-web 전제 폐기)
- 백엔드: Django 5.2 LTS + Django Ninja (ADR-0001)
- 태스크 추적: Linear — 팀 ASS, 프로젝트 "Assen 웹 플랫폼 v1" (구 "Assen Platform")

## 구조

| 경로 | 내용 |
|---|---|
| `web/` | **신방향 웹 앱** — React + Next.js 15 (DS 42 컴포넌트·전 라우트·React Query·B-API 연동) |
| `apps/` | Flutter 앱 — `fan_app`(팬+캐스트), `operator_app`(운영자/관리자) *(메이드era — M10 아카이브 대상)* |
| `packages/` | 공유 패키지 — core_tokens · ui_kit · api_client(재사용) · features · operator_features(폐기 대상) · test_fixtures |
| `server/` | Django 5.2 + Ninja 백엔드 (도메인 앱 24개 = 메이드era 19 + 신규 5: creator·social·content·commerce·membership) |
| `landing/` | 공개 랜딩 (Vite + GSAP — SEO 표면, Flutter 아님) |
| `docker-compose.yml` | 로컬/CI 개발 스택 (postgres · redis · api · celery worker/beat) |
| `.github/workflows/ci.yml` | CI 게이트 — lint/typecheck/test/빌드 스모크/compose/gitleaks |
| `scripts/` | 로컬 빌드, Compose smoke, production ECS deploy 준비 스크립트 |

## 문서

| 문서 | 내용 |
|---|---|
| `AGENTS.md` | 에이전트 하네스 (필수 선행 문서, 검증 계약, GitOps, 금지 영역) |
| `apps/AGENTS.md` · `server/AGENTS.md` | 스택별 중첩 하네스 |
| `docs/CONSTRAINTS.md` | 개발 제약사항 41개 (기준 문서) |
| `docs/adr/` | 아키텍처 결정 기록 |
| `docs/deployment.md` | 현재 배포 상태, local/dev build, production ECS deploy 절차 |
| `docs/research/` | 제약의 근거 리서치 (하네스 담론, 스택·IAP·컴플라이언스) |

작업 전 `AGENTS.md`(검증 계약·GitOps)와 `docs/CONSTRAINTS.md`를 읽을 것.

## 로컬 실행 / 빌드

```sh
scripts/build-local.sh   # Flutter web/APK + backend image build
scripts/up-local.sh      # postgres/redis/api/celery worker/beat 기동 + smoke
scripts/smoke-local.sh   # 이미 떠 있는 로컬 스택 smoke
```

Production 배포 준비와 현재 배포 상태는 `docs/deployment.md`를 기준으로 본다.
