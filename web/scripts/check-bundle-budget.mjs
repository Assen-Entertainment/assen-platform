/*
 * check-bundle-budget.mjs — 클라이언트 번들 회귀 게이트 (R6-W3).
 *
 * `next build` 산출물(.next/static/chunks)의 클라이언트 JS를 두 축으로 상한 검사한다:
 *   1) 총량(모든 청크 .js 합계) — 앱 전체 페이로드가 야금야금 커지는 회귀 차단.
 *   2) 최대 단일 청크 — 코드 스플릿 경계가 무너져 한 청크가 비대해지는 회귀 차단.
 * 위반 시 exit 1 + 위반 목록을 출력한다(라이브/mock 빌드 공통 — webpack 산출은 vitest 등
 * dev 툴체인과 무관하므로 두 빌드에서 동일 게이트).
 *
 * 실행: 먼저 빌드한 뒤(라이브 또는 mock) 이 스크립트를 돌린다.
 *   node scripts/check-bundle-budget.mjs
 * package.json: `npm run check:budget` (web-ci build job이 build 뒤 이 스텝을 게이트).
 *
 * ── 상한값 근거(2026-07-05 실측) ────────────────────────────────────────────
 * 실측(node 24, next 15, 이 브랜치): 라이브 빌드 총량 1,602.5 KB / 최대 청크 185.3 KB
 * (framework), mock 빌드 총량 1,611.6 KB / 최대 청크 185.3 KB. 두 빌드 사실상 동일.
 * 총량 상한 2,000 KB = 실측 대비 ~24% 여유(참고로 W3 지시서가 인용한 ~1,920 KB 상한 추정도
 * 상회하므로 측정 정의 차이로 인한 위양성도 흡수). 실사용 회귀(무거운 의존성 추가 등 ~400 KB
 * 증가)에서 발화한다. 최대 청크 상한 300 KB = 실측 185 KB 대비 ~62% 여유 — 벤더/라우트 청크가
 * 스플릿 경계를 넘겨 비대해지면 발화. 두 값 모두 "야금야금 성장은 허용하되 큰 회귀는 잡는" 수준.
 */
import { readdirSync, statSync } from "node:fs";
import { join, dirname, resolve, relative } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const webRoot = resolve(__dirname, ".."); // web/
const CHUNKS_DIR = join(webRoot, ".next", "static", "chunks");

// 상한(KB) — 근거는 파일 상단 주석 참조.
const TOTAL_BUDGET_KB = 2000;
const MAX_CHUNK_BUDGET_KB = 300;

/** CHUNKS_DIR 하위의 모든 .js를 재귀 수집해 [{path, bytes}]로 반환. */
function collectChunks(dir) {
  const out = [];
  for (const entry of readdirSync(dir, { withFileTypes: true })) {
    const full = join(dir, entry.name);
    if (entry.isDirectory()) {
      out.push(...collectChunks(full));
    } else if (entry.isFile() && entry.name.endsWith(".js")) {
      out.push({ path: full, bytes: statSync(full).size });
    }
  }
  return out;
}

const kb = (bytes) => bytes / 1024;
const fmt = (bytes) => `${kb(bytes).toFixed(1)} KB`;

let chunks;
try {
  chunks = collectChunks(CHUNKS_DIR);
} catch {
  console.error(
    `ERROR: ${relative(webRoot, CHUNKS_DIR)} 를 찾을 수 없습니다 — 먼저 \`npm run build\` 를 실행하세요.`,
  );
  process.exit(1);
}

if (chunks.length === 0) {
  console.error(`ERROR: ${relative(webRoot, CHUNKS_DIR)} 에 .js 청크가 없습니다 — 빌드 산출이 비었습니다.`);
  process.exit(1);
}

const totalBytes = chunks.reduce((sum, c) => sum + c.bytes, 0);
const largest = chunks.reduce((a, b) => (b.bytes > a.bytes ? b : a));

const violations = [];
if (kb(totalBytes) > TOTAL_BUDGET_KB) {
  violations.push(
    `총량 ${fmt(totalBytes)} > 상한 ${TOTAL_BUDGET_KB} KB (초과 ${(kb(totalBytes) - TOTAL_BUDGET_KB).toFixed(1)} KB)`,
  );
}
if (kb(largest.bytes) > MAX_CHUNK_BUDGET_KB) {
  violations.push(
    `최대 청크 ${relative(webRoot, largest.path)} ${fmt(largest.bytes)} > 상한 ${MAX_CHUNK_BUDGET_KB} KB`,
  );
}

console.log("번들 버짓 검사 (.next/static/chunks)");
console.log(`  청크 수:   ${chunks.length}`);
console.log(`  총량:      ${fmt(totalBytes)} / 상한 ${TOTAL_BUDGET_KB} KB`);
console.log(`  최대 청크: ${fmt(largest.bytes)} / 상한 ${MAX_CHUNK_BUDGET_KB} KB  (${relative(webRoot, largest.path)})`);

if (violations.length > 0) {
  console.error("\n번들 버짓 초과:");
  for (const v of violations) console.error(`  - ${v}`);
  // 상위 5개 청크를 함께 노출해 회귀 원인 진단을 돕는다.
  console.error("\n상위 5개 청크:");
  for (const c of [...chunks].sort((a, b) => b.bytes - a.bytes).slice(0, 5)) {
    console.error(`  ${fmt(c.bytes).padStart(10)}  ${relative(webRoot, c.path)}`);
  }
  process.exit(1);
}

console.log("\n번들 버짓 OK.");
