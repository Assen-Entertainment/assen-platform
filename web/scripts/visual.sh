#!/usr/bin/env bash
# 신뢰성 있는 시각 게이트 — 포트 선점 해제 → next start → visual-gate.mjs → 서버 종료.
# 사용(WSL/GitBash): bash web/scripts/visual.sh [PORT]
# ※ 포트 재사용 시 이전 stale 서버가 남아 잘못된 스크린샷이 찍히는 문제를 방지(선(先) kill).
PORT="${1:-3231}"
cd "$(dirname "$0")/.." || exit 1
for pid in $(netstat -ano 2>/dev/null | grep -E ":${PORT}[^0-9]" | awk '{print $NF}' | sort -u); do
  taskkill //F //PID "$pid" >/dev/null 2>&1 || true
done
npx next start -p "$PORT" > .next-start.log 2>&1 &
SRV=$!
node -e "const h=require('http');let n=0;const t=setInterval(()=>{h.get('http://localhost:${PORT}/',r=>{clearInterval(t);process.exit(0)}).on('error',()=>{if(++n>40){clearInterval(t);process.exit(1)}})},1000)"
echo "server ready:$?"
BASE_URL="http://localhost:${PORT}" node scripts/visual-gate.mjs
RC=$?
taskkill //PID "$SRV" //T //F >/dev/null 2>&1 || true
echo "visual exit:$RC"