# Assen B-API 레퍼런스 (v0.1)

> **정본 원칙: 코드 = 계약.** 이 문서는 사람이 읽는 레퍼런스이며, 기계 정본은
> `web/src/lib/api/openapi.json`(OpenAPI 3, 커밋됨)이다. 서버 스키마 변경 시
> `server/scripts/export_openapi.py` → `cd web && npm run gen:types`로 재생성한다.
> 대화형 문서: 서버 기동 후 **`/api/docs`**(Swagger UI) · 정적 HTML: `docs/api/reference.html`(Redoc).

- 베이스 URL: `{host}/api` (로컬: `http://127.0.0.1:8000/api`)
- 인증: **현재 전부 공개 읽기**(B2). Bearer(opaque+refresh)는 B3에서 도입 — 그 전까지 `following`/`liked`는 항상 `false`.
- CORS: 오리진 allow-list(`CORS_ALLOWED_ORIGINS`, 기본 차단). dev는 `localhost:3000` 기본 허용. (SDLC 11 §4)

## 공통 규약

**커서 페이지네이션** — 리스트 응답(wire, snake_case):
```json
{ "items": [ ... ], "next_cursor": "MjA=" }
```
`next_cursor`는 불투명 토큰(마지막 페이지=null). 요청 파라미터: `cursor`(이전 응답값), `limit`(1~100, 기본 20).

**에러** — `{ "detail": "creator not found" }` (404 등). 유효하지 않은 UUID/파라미터는 Ninja 검증으로 `422`.

**ID** — 도메인 리소스는 UUID. 시각은 ISO-8601(UTC).

## 엔드포인트 (B2 — 공개 읽기 9종)

### `GET /api/creators`
크리에이터 목록(핸들 순). 파라미터: `category?`, `cursor?`, `limit?`
```json
{ "items": [{ "id": "…", "handle": "stellar", "name": "별빛 일러스트", "bio": "…",
  "accent_color": "#E14B8A", "avatar_url": "", "cover_url": "", "category": "일러스트",
  "verified": true, "followers": 2, "posts": 2, "following": false }], "next_cursor": null }
```
`followers`/`posts`는 파생 카운트(저장 안 함, 드리프트 0).

### `GET /api/creators/{handle}`
핸들 단건. `handle`은 슬러그(`^[a-z0-9_]+$`). 미존재 → `404 {"detail":"creator not found"}`.

### `GET /api/posts`
포스트 목록(최신순). 파라미터: `creator_id?`(UUID — 크리에이터 스코프), `cursor?`, `limit?`
```json
{ "items": [{ "id": "…", "creator_id": "…", "creator_name": "별빛 일러스트",
  "creator_handle": "stellar", "verified": true, "body": "…", "media_url": "",
  "like_count": 0, "comment_count": 2, "liked": false, "created_at": "2026-07-02T…Z" }], "next_cursor": null }
```

### `GET /api/posts/{post_id}`
포스트 단건(UUID). 미존재 → 404.

### `GET /api/posts/{post_id}/comments`
포스트 댓글(오래된 순, 페이지). 항목: `{ id, post_id, author, body, created_at }` — `author`는 **표시명만**(내부 식별자 비노출).

### `GET /api/feed`
익명 피드 = 전 크리에이터 최신 포스트(페이지, PostOut 동일). B3 후 개인화(팔로잉) 피드의 배선 지점.

### `GET /api/products`
상품 카탈로그(최신순, 페이지). 파라미터: `creator_id?`, `product_type?`(`goods|digital|experience|ticket|coupon`)
항목: `{ id, creator_id, type, title, price, meta, media_url }` — `price`=정수 KRW **표시값**(정산 아님).

### `GET /api/tiers`
멤버십 티어(정렬순, **비페이지 배열** — 상한 100). 파라미터: `creator_id?`
항목: `{ id, creator_id, name, price, period, benefits[], badge, featured, sort_order }`

### `GET /api/search?q=`
통합 검색(각 최대 10건, `q`≤100자): `{ "creators": [CreatorOut…], "products": [{ id, type, title, price, meta }…] }`
크리에이터=이름/핸들 부분일치, 상품=제목 부분일치. 빈 질의 → 빈 결과.

### `GET /api/health` · `GET /healthz`
`/api/health` → `{ status, version, commit }`. `/healthz` → 인프라 프로브용 bare 200(프로덕션 SSL 리다이렉트 면제).

## 예정 계약 (게이트 — 문서화만, 미구현)

| 단계 | 엔드포인트(안) | 게이트 |
|---|---|---|
| B3 | `POST /api/auth/login` · `/refresh` · `/social/{provider}` · `/verify-age` | 본인인증 벤더·#26 |
| B4 | `POST /api/creators/{handle}/follow` · `POST /api/posts/{id}/like` · `POST /api/posts/{id}/comments` | — (B3 의존) |
| B6 | `WS /ws/chat/{conversationId}` · `WS /ws/notifications` | — |
| B7 | `POST /api/orders` · `POST /api/subscriptions` | 결제·정산(대표·법무·PG) |

## 클라이언트 소비

- **웹**: `web/src/lib/api/index.ts`(snake→camel 매핑·mock 폴백) + React Query 훅(`queries.ts`). 타입은 `schema.d.ts`(openapi-typescript 생성).
- **모바일(M4 예정)**: 동일 openapi.json → Dart 모델 코드젠.
