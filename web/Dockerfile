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
ARG NEXT_PUBLIC_SITE_URL
ARG NEXT_PUBLIC_API_URL
ENV NEXT_PUBLIC_SITE_URL=${NEXT_PUBLIC_SITE_URL} \
    NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL} \
    NEXT_TELEMETRY_DISABLED=1
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
# public/ 은 현재 없음 — 생기면 아래 주석 해제
# COPY --from=build --chown=node:node /app/public ./public
EXPOSE 3000
CMD ["node", "server.js"]
