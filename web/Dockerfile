# Assen web (Next.js 15, standalone) — ECS/컨테이너 경로 패키징 (SDLC 11 §3).
# 호스팅 최종 결정(E10: Vercel vs ECS)은 게이트 — 본 이미지는 ECS 경로 준비물이며
# Vercel 채택 시 사용하지 않는다(next.config의 output:"standalone"은 양쪽 무해).
#
# NEXT_PUBLIC_* 는 빌드 타임에 번들로 인라인되므로 build-arg로 주입한다:
#   docker build --build-arg NEXT_PUBLIC_API_URL=https://api.example.com/api -t assen-web web/

# --- deps + build ---------------------------------------------------------
FROM node:22-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --legacy-peer-deps
COPY . .
# NEXT_PUBLIC_SITE_URL: build-arg 미지정 시에도 빈 문자열이 새지 않도록 기본값을 준다 —
# 빈 NEXT_PUBLIC_SITE_URL은 metadataBase의 new URL("")을 깨뜨린다(config.ts 참조).
ARG NEXT_PUBLIC_SITE_URL=http://localhost:3000
# NEXT_PUBLIC_API_URL: 기본값 없음(빈 값 = mock 모드). 배포 이미지는 반드시 주입해야 하며,
# 누락 시 아래 프로드 가드가 이미지 빌드를 실패시킨다.
ARG NEXT_PUBLIC_API_URL=
ENV NEXT_PUBLIC_SITE_URL=${NEXT_PUBLIC_SITE_URL} \
    NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL} \
    NEXT_TELEMETRY_DISABLED=1
# 프로드 가드 — 배포 가능한 이미지는 NEXT_PUBLIC_API_URL이 반드시 있어야 한다. 비어 있으면
# middleware.ts의 MOCK_MODE가 빌드타임에 true로 인라인되어 인증 가드가 조용히 영구 비활성된다
# (런타임 env로는 되돌릴 수 없다). 값이 비면 여기서 빌드를 실패시켜 auth 없는 이미지 배포를 원천 차단.
# ※ mock 빌드(`npm run build`를 Docker 밖에서 직접 실행)는 이 가드에 영향받지 않는다.
#    CI 컨테이너 패키징 스모크(web-ci.yml)는 비배포 placeholder API URL을 주입해 패키징만 검증한다.
RUN test -n "$NEXT_PUBLIC_API_URL" || (echo "ERROR: deployable image requires the NEXT_PUBLIC_API_URL build-arg — auth middleware (middleware.ts MOCK_MODE) would be silently disabled; do not ship a mock build" >&2 && exit 1)
RUN npm run build

# --- runtime --------------------------------------------------------------
FROM node:22-alpine AS runtime
WORKDIR /app
ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    PORT=3000 \
    HOSTNAME=0.0.0.0
# 비루트 실행 (이미지 기본 node 유저)
USER node
COPY --from=build --chown=node:node /app/.next/standalone ./
COPY --from=build --chown=node:node /app/.next/static ./.next/static
# public/ (폰트 등 정적 자산) — standalone은 public을 자동 포함하지 않으므로 명시 복사.
COPY --from=build --chown=node:node /app/public ./public
EXPOSE 3000
CMD ["node", "server.js"]
