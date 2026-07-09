# Assen B-API 레퍼런스

> **정본 원칙: 코드 = 계약.** 기계 정본은 `web/src/lib/api/openapi.json`(OpenAPI 3, 커밋됨).
> 서버 스키마 변경 시 `server/scripts/export_openapi.py` → `cd web && npm run gen:types`로
> 재생성한다. 대화형 문서: 서버 기동 후 **`/api/docs`**(Swagger UI) · 정적 HTML:
> `docs/api/reference.html`(Redoc).
>
> 실 API 표면은 `server/config/api.py`에 등록된 **~21개 도메인 라우터**
> (`apps/{admin_rbac,cast,cheki,commerce,content,coupon,creator,dashboard,
> event_campaign,identity,membership,notification,payments,pos_lite,reservation,
> safety,schedule,social,uploads,visit,visit_guide}/api.py`)다. 엔드포인트 산문 나열은
> 여기서 관리하지 않는다 — 코드와 드리프트하는 원천이라 R11(2026-07-09) 문서 고도화에서
> 제거했다. 개별 엔드포인트는 `/api/docs`에서 확인한다.

## 공통 규약

**베이스 URL**: `{host}/api` (로컬: `http://127.0.0.1:8000/api`)

**커서 페이지네이션** — 리스트 응답(wire, snake_case):

```json
{ "items": [ ... ], "next_cursor": "MjA=" }
```

`next_cursor`는 불투명 토큰(마지막 페이지=null). 요청 파라미터: `cursor`(이전 응답값),
`limit`(1~100, 기본 20).

**에러 taxonomy** — 응답 바디는 `{ "detail": "...", "code": "..." }`. `detail`은 사람이
읽는 카피(로케일 종속, 바뀔 수 있음) — 클라이언트는 `detail` 문자열이 아니라 안정적인
`code`(PascalCase, 예: `AccountNotRegistered`·`ProductNotFound`)로 분기한다. `code`는
**추가만 가능한 계약**이다 — 기존 값은 절대 이름을 바꾸지 않는다(`server/config/errors.py`
`ErrorCode`가 정본). 유효하지 않은 UUID/파라미터는 Ninja 검증으로 `422`.

**인증**: `Authorization: Bearer <access token>`(opaque + refresh 회전, ADR-0002).
웹은 httpOnly 쿠키 델리버리도 병행(`identity.auth`).

**ID / 시각**: 도메인 리소스는 UUID. 시각은 ISO-8601(UTC).

**CORS**: 오리진 allow-list(`CORS_ALLOWED_ORIGINS`, 기본 차단). dev는 `localhost:3000` 기본
허용(SDLC 11 §4).

## 클라이언트 소비

- **웹**: `web/src/lib/api/index.ts`(snake→camel 매핑·mock 폴백) + React Query 훅
  (`queries.ts`). 타입은 `schema.d.ts`(openapi-typescript 생성, `npm run gen:types`).
- **모바일**: 동일 `openapi.json` → Dart 모델 코드젠(`api_client` 패키지).
- **헬스체크**: `GET /api/health` → `{ status, version, commit }`. `GET /healthz` → 인프라
  프로브용 bare 200(프로덕션 SSL 리다이렉트 면제).
