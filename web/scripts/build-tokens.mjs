/*
 * build-tokens.mjs — docs/design/tokens.v2.json → web/src/styles/tokens.css 재생성.
 * 디자인 토큰 단일 소스(tokens.v2.json)에서 웹 CSS 변수(라이트 :root / 다크 .dark)를 투영한다.
 * 실행(WSL): node web/scripts/build-tokens.mjs   (커밋된 tokens.css 는 이 스크립트의 출력)
 * Dart(core_tokens)·랜딩(landing) 타깃은 tools/tokens/build.mjs (별개). 향후 G012 리워크 시 통합 고려.
 */
import { readFileSync, writeFileSync, mkdirSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const repo = resolve(__dirname, "..", ".."); // assen-platform/
const tokens = JSON.parse(readFileSync(resolve(repo, "docs/design/tokens.v2.json"), "utf8"));

const getNode = (path) => path.split(".").reduce((o, k) => (o == null ? o : o[k]), tokens);
function resolveColor(v) {
  const m = typeof v === "string" && /^\{(.+)\}$/.exec(v);
  return m ? resolveColor(getNode(m[1]).$value) : String(v).toLowerCase();
}

// color.sys 키 → CSS 변수명
const SYS = {
  surface: "surface", surfaceContainer: "surface-container",
  surfaceContainerHigh: "surface-container-high", onSurface: "on-surface",
  onSurfaceVariant: "on-surface-variant", outline: "outline", outlineVariant: "outline-variant",
  primary: "primary", primaryHover: "primary-hover", onPrimary: "on-primary", primaryContainer: "primary-container",
  onPrimaryContainer: "on-primary-container", secondary: "secondary",
  error: "error", onError: "on-error", errorContainer: "error-container",
  onErrorContainer: "on-error-container", success: "success", warning: "warning",
  successContainer: "success-container", onSuccessContainer: "on-success-container",
  warningContainer: "warning-container", onWarningContainer: "on-warning-container",
};
const sysBlock = (key) =>
  Object.entries(SYS)
    .map(([k, name]) => `  --${name}: ${resolveColor(tokens.color[key][k].$value)};`)
    .join("\n");

const g = tokens.gradient.brand.$value;
const c = tokens.chart;
const chartLight =
  [1, 2, 3, 4, 5, 6, 7, 8].map((n) => `  --chart-${n}: ${resolveColor(c.categorical[n].$value)};`).join("\n") +
  `\n  --chart-positive: ${resolveColor(c.positive.$value)};` +
  `\n  --chart-negative: ${resolveColor(c.negative.$value)};` +
  `\n  --chart-axis: ${resolveColor(c.axis.$value)};` +
  `\n  --chart-grid: ${resolveColor(c.grid.$value)};`;

const out = `/*
 * Assen 웹 디자인 토큰 — docs/design/tokens.v2.json 미러 (web). GENERATED — build-tokens.mjs.
 * 라이트 = :root, 다크 = .dark. 무접두 원시 CSS변수 → globals.css @theme inline.
 */
:root {
${sysBlock("sys")}

  --gradient-brand: linear-gradient(${g.angle}deg, ${g.stops[0].toLowerCase()} 0%, ${g.stops[1].toLowerCase()} 100%);

  --creator-accent: ${resolveColor(tokens.color.sys.primary.$value)};
  --creator-accent-hover: ${resolveColor(tokens.color.sys.primaryHover.$value)};
  --on-creator-accent: #ffffff;
  --creator-accent-container: ${resolveColor(tokens.color.sys.primaryContainer.$value)};
  --on-creator-accent-container: ${resolveColor(tokens.color.sys.onPrimaryContainer.$value)};

${chartLight}
}

.dark {
${sysBlock("sysDark")}

  --chart-axis: ${resolveColor(c.axisDark.$value)};
  --chart-grid: ${resolveColor(c.gridDark.$value)};
}
`;

const dest = resolve(__dirname, "..", "src/styles/tokens.css");
mkdirSync(dirname(dest), { recursive: true });
writeFileSync(dest, out);
console.log(`[assen web tokens] wrote ${dest}`);
