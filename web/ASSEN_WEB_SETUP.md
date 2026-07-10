# Assen 웹 클라이언트 — 셋업 가이드 (React + Next.js + Tailwind v4 + Radix)

> 스택 결정 = [[assen-web-stack]] · SDLC 08 · `docs/adr/0005-web-react-next.md`. 빌드/설치/실행은 **Windows npm**(node 24 / npm 11, `docs/adr/0006-toolchain-windows-uv.md` — pnpm·WSL 불요).
> 스캐폴드는 완료 상태다: `web/`은 실행 가능한 앱(전 라우트·DS 42 컴포넌트·React Query·테스트·B5 실 API 연동)이며, 본 문서는 로컬 구동·검증 절차만 다룬다.

## 1. 설치 & 실행 (Windows)
```bash
cd assen-platform/web
npm install --legacy-peer-deps   # react 19 peer 경고 회피
npm run dev                      # http://localhost:3000
```

## 2. npm 스크립트
| 스크립트 | 역할 |
|---|---|
| `npm run dev` | 개발 서버 |
| `npm run build` | 프로덕션 빌드 (**타입체크 + ESLint 게이트 포함**) |
| `npm run start` | 프로덕션 서버 (`-p <port>` 지정 가능) |
| `npm run lint` | ESLint (flat config, `eslint.config.mjs`) |
| `npm test` | Vitest (jsdom + Testing Library) |
| `npm run gen:types` | `src/lib/api/openapi.json` → `schema.d.ts` (openapi-typescript) |

## 3. 환경변수 (`.env.example` → `.env.local`)
| 변수 | 의미 |
|---|---|
| `NEXT_PUBLIC_SITE_URL` | 사이트 절대 URL (metadataBase·sitemap) |
| `NEXT_PUBLIC_API_URL` | 백엔드 B-API 베이스 (예: `http://127.0.0.1:8000/api`). **미설정 시 `lib/api`가 in-file mock으로 폴백** — 백엔드 없이 빌드/SSG/개발 가능 (B5) |

백엔드 연동 계약은 코드가 정본: `openapi.json`은 `server/scripts/export_openapi.py`로 백엔드에서 재생성 → `npm run gen:types`로 타입 재생성.

## 4. 구조 (현행)
| 경로 | 역할 |
|---|---|
| `src/styles/tokens.css` | 디자인 토큰 CSS 변수(라이트 `:root`/다크 `.dark`) — **tokens.v2.json 미러** (`node scripts/build-tokens.mjs`로 재생성) |
| `src/styles/globals.css` | Tailwind v4 `@theme` 배선(색/radius/타이포/shadow) + 다크 variant |
| `src/lib/creator-accent.ts` | 크리에이터 액센트(WCAG 자동대비) `creatorAccentVars()` |
| `src/lib/icons.ts` | Material 아이콘 시맨틱 레지스트리(react-icons/md) |
| `src/lib/api/` | 도메인 API 레이어 — 실 API(`NEXT_PUBLIC_API_URL`) ↔ mock 폴백, snake→camel 매핑, React Query 훅(`queries.ts`) |
| `src/components/ui/` | DS 컴포넌트 42종 + 배럴(`index.ts`) — 전체 쇼케이스는 `/gallery` |
| `src/app/` | App Router 화면 전체(discovery·creator/[handle]·feed·post/[id]·store·membership·checkout·studio·mypage·설정·인증 진입 등) |

## 5. 검증
```bash
npm run build   # 타입 0오류 + ESLint 게이트 + SSG
npm test        # Vitest 스위트
npm run dev     # /gallery 에서 42 컴포넌트 라이트/다크·creatorAccent 확인
```
- 시각 회귀 게이트(스크린샷 ↔ Figma 비교)는 `ASSEN_DS_VISUAL_GATE.md` 참조.
- 폰트(Pretendard Variable)는 추후 `next/font/local` 번들 예정(모바일 `tools/fonts/setup_pretendard.sh`와 동일 패밀리). 미설치 시 Apple SD Gothic Neo/sans-serif 폴백.
