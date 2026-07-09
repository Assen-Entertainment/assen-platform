# Assen `feature/prod-parity-env` — 외부 검증 도시에 (Validation Dossier)

> **목적**: 이 문서 하나로 외부 validator(리뷰어·QA·감사자·타 팀)가 이 브랜치의 작업을
> **독립적으로 재현·검증**할 수 있게 한다. 각 영역마다 *변경 내용 · 검증 명령 · 기대 결과 · 상태*를 명시한다.
> 신뢰의 근거는 주장이 아니라 **재현 가능한 명령과 그 출력**이다.

- **작성일**: 2026-07-10
- **브랜치**: `feature/prod-parity-env` (origin 반영됨)
- **검증 본체 HEAD**: `caa0f28` — origin/dev 대비 **28 커밋**
- **베이스**: `origin/dev`
- **이슈 추적**: Linear 프로젝트 "프로덕션 준비 고도화" — `ASS-261 ~ ASS-283`
- **⚠️ 진행 중(아직 검증 대상 아님)**: 엔지니어링 고도화 배치 B1~B5(문서·DevOps·Backend·Frontend·Mobile)가 autopilot으로 **실행 중이며 미커밋**. 본 도시에는 `caa0f28` 스냅샷 기준이다. (§7)

---

## 0. 검증 환경 재현 (Windows 기준)

이 리포는 **순수 Windows** 개발 환경이다(WSL 제거, 2026-07-01). 도구: `.venv-win`(Python, uv), Node/npm, `C:\Users\daisy\flutter`(Flutter 네이티브), Docker Desktop(Postgres 16 + Redis 7).

```powershell
# 0-1. 리포 + 브랜치
git fetch origin; git checkout feature/prod-parity-env

# 0-2. 데이터 스토어 (프로덕션-패리티: Postgres 16 / Redis 7)
docker compose up -d postgres redis          # 헬시 확인: docker compose ps

# 0-3. 서버 파이썬 환경 (★반드시 .venv-win 대상)
cd server
$env:UV_PROJECT_ENVIRONMENT = ".venv-win"
.\.venv-win\Scripts\uv.exe sync --frozen --extra realtime-redis    # Pillow·channels-redis 포함

# 0-4. 웹
cd ..\web; npm ci --legacy-peer-deps

# 0-5. 모바일 (패키지별, 루트 pub get 금지)
cd ..\apps\assen_mobile; C:\Users\daisy\flutter\bin\flutter pub get
```

**★재현 함정 (반드시 숙지)**
- `uv sync`(전체 재조정)는 **실행 중인 dev 서버가 `.venv-win\Scripts\*.pyd`를 잠그면 실패**한다. → 서버 정지 후 실행하거나, 상시 가산 설치는 `uv pip install --python .venv-win\Scripts\python.exe <pkg>`.
- uv는 stale `.venv`(POSIX 잔재)를 기본 타깃하니 항상 `UV_PROJECT_ENVIRONMENT=.venv-win`.
- `test_pg`(실 Postgres) 검증은 0-2의 docker Postgres가 떠 있어야 한다.

---

## 1. 검증 매트릭스 (규율별 · 명령 · 기대 결과)

| 규율 | 검증 명령 (해당 디렉토리에서) | 기대 결과 |
|---|---|---|
| **Backend 단위/통합** | `cd server; $env:DJANGO_SETTINGS_MODULE="config.settings.test"; .\.venv-win\Scripts\python.exe -m pytest -q` | **819 passed, 0 failed** |
| **Backend on Postgres** | `.\.venv-win\Scripts\python.exe -m pytest --ds=config.settings.test_pg apps/creator config/tests/test_pagination.py -q` | **all passed** (검색 Case/When·keyset seek 실 DB 검증) |
| **Backend 타입** | `.\.venv-win\Scripts\python.exe -m mypy .` | **Success: no issues found in 285 source files** |
| **Backend 린트** | `.\.venv-win\Scripts\python.exe -m ruff check .` | migrations 자동생성 파일 외 **clean** |
| **Backend 레이트리밋(라이브 Redis)** | `.\.venv-win\Scripts\python.exe -m pytest config/tests/test_ratelimit.py -q` | **11 passed** (Redis 없으면 라이브 4종 skip) |
| **Web 타입** | `cd web; npx tsc --noEmit` | **0 errors** |
| **Web 린트** | `npm run lint` | **clean** |
| **Web 빌드 + 번들예산** | `npm run build; npm run check:budget` | **build 성공 · budget PASS** (2110/2620KB) |
| **Web 단위** | `npx vitest run` | **229 passed** (45 files) |
| **Mobile 정적분석** | `cd apps\assen_mobile; C:\Users\daisy\flutter\bin\flutter analyze` | **No issues found** (core_tokens·ui_kit도 각각) |
| **Mobile 테스트** | `C:\Users\daisy\flutter\bin\flutter test` | **124 passed** (core_tokens 22 · ui_kit 189 · app 124) |
| **DevOps compose** | `docker compose config -q` | **exit 0 (valid)** |
| **시크릿 스캔** | `gitleaks detect --source .` (설치 시) | **0 leaks** (CI 최종 게이트) |

> 최신 통합 실행 기준 카운트다. 커밋 시점별 카운트는 각 커밋 메시지에 명시돼 있다.

---

## 2. 핵심 불변식 스팟체크 (validator 직접 확인용)

```powershell
# 2-1. prod 설정 fail-closed (DATABASE_URL 부재 → 부팅 차단)  [ASS-265]
cd server
$env:DJANGO_SETTINGS_MODULE="config.settings.prod"; $env:DJANGO_SECRET_KEY="x"; $env:DJANGO_ALLOWED_HOSTS="localhost"
$env:CELERY_BROKER_URL="redis://x"; $env:CELERY_RESULT_BACKEND="redis://x"
.\.venv-win\Scripts\python.exe -c "import django; django.setup()"
#   기대: django.core.exceptions.ImproperlyConfigured: Set the DATABASE_URL environment variable

# 2-2. 마이그레이션 정식 전환 (모델↔마이그레이션 동기)  [ASS-266]
$env:DJANGO_SETTINGS_MODULE="config.settings.test"
.\.venv-win\Scripts\python.exe manage.py makemigrations --check --dry-run
#   기대: No changes detected  (exit 0)

# 2-3. 랭킹·페이지네이션 검색 (라이브 API, 스택 가동 시)  [ASS-273]
curl "http://127.0.0.1:8000/api/search?q=a&limit=2"        # 기대: {creators[], products[], next_offset}
curl "http://127.0.0.1:8000/api/creators?sort=popular"      # 기대: 팔로워순 랭킹 items

# 2-4. CSP report-only (강제 CSP 미방출)  [ASS-278]
#   test_middleware.py::test_security_headers_include_report_only_csp_not_enforced 가 계약 검증

# 2-5. 다크모드 AA 전경 (모바일)  [ASS-282]
#   packages/core_tokens: indigoTextDark(#A79BFF ≈8:1) — 순수 전경 4개 컴포넌트가 이를 소비
```

**보안·위생 스팟체크**
- 저장 PII 0: 업로드는 서버-민팅 UUID만, OTP/전화번호 미영속(`server/config/otp.py`).
- 결제·정산 금액 없음: 이번 브랜치는 **mock PG·카운트만**, 실 금액 게이트는 fail-closed 503.
- 임시 스크립트 잔여 0: `git status`에 QA 드라이버(`web/qa-*.mjs`) 등 없음(전량 삭제됨).

---

## 3. 커밋 인벤토리 (28 · 프로그램 단계별)

각 커밋은 focus 단위이며, ASS 이슈·검증 포인트를 커밋 메시지에 담고 있다.

### Phase A — 기반: 마이그레이션·디자인·프로덕션-패리티 테스트
| 커밋 | 요약 | 검증 |
|---|---|---|
| `e50e813` | 23개 도메인 앱 initial migrations (#25 전환) | §2-2 |
| `af342e9` | 브랜드색 #5A4DF0(Fanding 톤) 정본 확정 | tokens.v2.json |
| `3d4e7c6` | 실 Postgres(test_pg) 스위트 + keyset sqlite 가정 수정 | §1 Backend-PG |
| `882e1e3` | Pretendard 번들 + display 폰트 정본 토큰 | web build |
| `73e2965` | 웹 디자인 9점 폴리시(프론트도어·mesh·커버깊이·모션) | §1 Web build |
| `a998e29` | 모바일 인디고 팔레트 전면 이관(하츠코이→v2) | flutter test |
| `84cf298` | 모바일 브랜드 표현 웨이브(락업·그라디언트·paper·모션) | flutter test |
| `eddfa91` | 모바일 브랜드 그라디언트 텍스트 AA scrim | flutter test |
| `b9bf4e0` | 디스커버리 썸네일 리치 메시(라이브 QA 발견) | web build |
| `2cc59af` | 다크 text-primary AA 대비 리프트(#A79BFF) | axe-core 재감사 |
| `489f258` | 2026-07-08 코드→Figma 역동기 기록 | docs |

### Phase B — 프로덕션 준비 로드맵 + 착수 배치 1
| 커밋 | 요약 | 검증 |
|---|---|---|
| `9d96902` | production-readiness 고도화 로드맵(ASS-261..283) | `docs/ops/production-readiness-2026-07-09.md` |
| `a89302c` | prod DATABASE_URL/celery fail-closed (ASS-265) | §2-1 |
| `b5269b8` | 마이그레이션 정식 전환 문서·스크립트 (ASS-266) | §2-2 |
| `ab0e30a` | dev compose api daphne(ASGI)+healthcheck (ASS-268) | `docker compose config` |
| `d27a6a6` | SSR-only 뷰 에러상태 + dev 라우트 noindex (ASS-275/276) | web tsc/lint |

### Phase C — 착수 가능 게이트 (ultragoal)
| 커밋 | 요약 | 검증 |
|---|---|---|
| `13b2d64` | CSP report-only + 1yr HSTS (ASS-278) | §1 · test_middleware |
| `e76278b` | CI 커버리지·Storybook·Android PR·CodeQL·Dependabot (ASS-279) | YAML valid |
| `a7fd0ad` | 랭킹 다필드 검색 + 서버 추천 정렬 (ASS-273/274) | §2-3 · creator tests |
| `4144881` | 웹 검색 load-more + 서버정렬 셸프 (ASS-273/274) | vitest |
| `62d4b49` | 모바일 다크 파운데이션 + AA indigoText (ASS-282) | flutter test |

### Phase D — 잔여 게이트 착수 가능분
| 커밋 | 요약 | 검증 |
|---|---|---|
| `167da52` | 실 RedisRateLimiter(원자 Lua)+런타임 fail-safe (ASS-268) | §1 test_ratelimit |
| `af69ea4` | Studio 실 집계 카운트(판매·구독자, 금액 없음) (ASS-264) | commerce/membership test_studio |
| `28daea3` | 모바일 인앱 테마 토글 (ASS-282) | flutter test |

### Phase E — 의존 추가 웨이브 (대표 승인)
| 커밋 | 요약 | 검증 |
|---|---|---|
| `e63fe7d` | Pillow 디코드-검증 + 압축폭탄 가드 (ASS-271) | uploads tests |
| `88f4dcb` | channels-redis 크로스워커 레이어 배선 (ASS-268) | test_channel_layers |
| `5d2925e` | env-gated 웹 Sentry (ASS-270) | web build(DSN 유·무) |
| `caa0f28` | shared_preferences 테마 영속화 (ASS-282) | flutter test |

### Phase F — 엔지니어링 품질 고도화 (5축 조사 기반 · 계약 무관 · autopilot)
| 커밋 | 요약 | 검증 |
|---|---|---|
| `66f5fd7` | 외부 검증 도시에(본 문서) | self |
| `73394d3` | 문서 stale 스윕 + 발견성(PR템플릿 유해정정·API README·ADR 0005/0006·docs 인덱스·온보딩) | 상대경로 실존·잔존문구 0 |
| `cbf83f9` | 공급망 위생·CI캐시·non-root 이미지·digest핀·Windows dev DX(부트스트랩/닥터·justfile·Trivy SCA/SBOM) | YAML·compose·hadolint·just clean |
| `15a9cde` | LazyMotion(−45KB)·jsx-a11y 게이트(14위반)·LoadMore·noUncheckedIndexedAccess(13지점) | web tsc/lint/build+예산/vitest 229 |
| `f848dd8` | 타입 접근자(cast+ignore 64 제거)·머니 구조화로깅·Postgres 동시성테스트 3·throttle +31·ruff migrations 제외 | ruff clean·mypy 286·pytest **821**+동시성 3(PG) |
| _(B5 Mobile)_ | 진행 중 — 에러매퍼·a11y 3→13·refresh 베이스·픽스처 중앙화·golden CI(Linux) | _(커밋 후 추가)_ |

> **Phase F 회귀 방지 특기**: B3 ruff `--fix`가 생성 마이그레이션 21개를 오염 → **되돌림 + ruff에 `**/migrations/**` 제외 추가**(mypy 미러)로 재발 차단. golden(모바일)은 #31·CI(Linux) 제약으로 **로컬 미생성**, `golden.yml` workflow_dispatch(대표 1클릭)가 Linux 베이스라인 생성.

---

## 4. 독립 검증 체크리스트

- [ ] §1 매트릭스 전 항목 기대 결과 일치 (pytest 819 · mypy 285 · web tsc/lint/build/vitest · flutter analyze/test)
- [ ] §2-1 prod fail-closed 재현 (DATABASE_URL 부재 → ImproperlyConfigured)
- [ ] §2-2 `makemigrations --check` → "No changes detected"
- [ ] §2-3 검색이 랭킹·`next_offset` 반환 / `sort=popular` 랭킹
- [ ] §1 RedisRateLimiter 11 passed (라이브 Redis 시 4종 pass, 없으면 skip)
- [ ] `docker compose config -q` valid
- [ ] gitleaks 0 leaks · 저장 PII 0 · 임시 스크립트 잔여 0
- [ ] 각 커밋이 단일 focus이며 메시지의 검증 주장과 코드가 일치

---

## 5. 리뷰 판정 이력 (evidence)

- **code-reviewer**: 각 웨이브 **APPROVE**. 발견된 HIGH 2건은 **수정 후 통과**:
  - RedisRateLimiter의 fail-safe가 init 시점만 보호 → 런타임 예외 시 in-memory 폴백 추가(`167da52`).
  - channel-layer redis 테스트가 CI(extra 미설치)서 fail → `pytest.importorskip("channels_redis")`(`88f4dcb`).
- **critic (디자인·UX·워크플로)**: **ACCEPT-WITH-RESERVATIONS → ACCEPT**. P1 3건(상품 셸프 과잉약속 카피·모바일 다크 인디고 sub-AA·검색 탭 빈상태) **수정 완료**.
- **라이브 Playwright QA**: 표면 12/12 · 심층 9/9 · 크리에이터/스튜디오 11/11 · a11y 5/5(수정 후 0 위반) · 에러내성 5/5 · 검색/추천 3/3, page error 0.

---

## 6. 미완 / 차단 (검증 범위 밖, 정직 고지)

- **외부 계약·계정 선행 게이트** (mock/fail-closed 상태로 존재, 검증 대상 아님): PG(261)·KYC(262)·실SMS(263)·정산 확정금액(264, PG후행)·클라우드 IaC(267)·FCM/APNs(269)·S3 스토리지+모더레이션(271)·백업/PITR(272)·IAP(280). 상세: `docs/ops/production-readiness-2026-07-09.md`.
- **모바일 golden 테스트(34개)**: `skip: true` 상태(픽셀 회귀 커버리지 0). `#31` 인간 게이트(`scripts/hooks/guard.py`가 `--update-goldens`·`goldens/` 하드 차단). CI(Linux) 베이스라인 생성 워크플로가 별도 배치(B5)에서 배선 중 — 대표 1회 `workflow_dispatch` 트리거가 잠금해제.
- **i18n(277)**: 단일 로케일(ko), 2차 로케일 사업 결정 대기(근거 후행).

---

## 7. 진행 중 — 엔지니어링 고도화 배치 (미커밋, 아직 검증 대상 아님)

`caa0f28` 이후, autopilot으로 5개 품질 배치가 실행됐다. **B1·B2·B3·B4는 커밋 완료(§3 Phase F)**, **B5(Mobile+golden CI)만 진행 중**이다.
- **B1 문서** stale 스윕(PR템플릿 유해정정·API README·피벗 ADR·인덱스·온보딩)
- **B2 DevOps** 위생·DX(Windows 부트스트랩/닥터·npm ci·CI 캐시·SCA/SBOM·digest핀·non-root)
- **B3 Backend** 타입 접근자(60 cast 제거)·머니경로 로깅·동시성 테스트·throttle
- **B4 Frontend** LazyMotion·jsx-a11y·noUncheckedIndexedAccess·LoadMore·RQ retry
- **B5 Mobile** 에러매퍼·a11y 3→13·refresh 베이스·픽스처 중앙화·golden CI(Linux)

각 배치는 구현 → QA(테스트 green) → code-review → 이슈별 커밋을 거친다. 검증 방법은 §1 매트릭스와 동일하다.

---

## 8. 도시에 유지보수

- 이 스냅샷은 `caa0f28` 기준. 신규 커밋 병합 시 §3에 행 추가 + §1 카운트 갱신.
- 정본 근거: 각 커밋 메시지 + Linear ASS-261~283 코멘트 + `docs/ops/production-readiness-2026-07-09.md`.
- 문의 시 재현 명령의 **정확한 출력**을 첨부해 논의한다(주장 아닌 증거).
