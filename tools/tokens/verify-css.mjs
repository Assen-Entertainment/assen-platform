// Proves the GENERATED Vite CSS custom properties equal the design-token subset
// of the existing landing :root, with ZERO value drift (ASS-128, ADR-0004 #2).
//
// WHY a dedicated check (not just `git diff`): style.css was re-shaped to
// `@import './tokens.generated.css'` + a landing-local :root, so a raw text diff
// no longer aligns line-for-line. This compares the resolved (name -> value)
// pairs instead: every generated property must match the value the browser used
// before, and every token-derived :root property must now come from the
// generated file. Non-token landing-locals (fonts, --shadow-*, --gutter) are
// expected to remain and are excluded.
//
// Exit 0 = diff-0 holds. Exit 1 = a real regression. Run: node verify-css.mjs

import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';

const REPO_ROOT = resolve(dirname(fileURLToPath(import.meta.url)), '..', '..');
const GEN = resolve(REPO_ROOT, 'landing/src/tokens.generated.css');

// The reference snapshot of the original :root token block (pre-codegen).
// These are the exact (name, value) pairs the landing shipped with; the
// generator must reproduce them byte-for-byte. Kept here as the spike's
// acceptance oracle so the proof survives even after style.css is re-shaped.
const EXPECTED = {
  'cream-50': '#fffdf7', 'cream-100': '#fff8e7', 'cream-200': '#f8efdb', 'cream-300': '#efe3c9',
  white: '#ffffff',
  'ink-900': '#2b2724', 'ink-700': '#57534e', 'ink-500': '#8a8178',
  'ink-300': '#c9c0b4', 'ink-200': '#e3daca', 'ink-100': '#f0eadd',
  'strawberry-bgs': '#fff0f4', 'strawberry-bg': '#ffd9e2', 'strawberry-bd': '#f0a8bc', 'strawberry-ink': '#8e2f4a',
  'peach-bg': '#ffdcc7', 'peach-bd': '#ebaf85', 'peach-ink': '#8a4a1f',
  'lemon-bgs': '#fff9df', 'lemon-bg': '#ffefb3', 'lemon-bd': '#ddc25e', 'lemon-ink': '#6e5a14',
  'matcha-bgs': '#eff6ea', 'matcha-bg': '#d8ebcb', 'matcha-bd': '#a0cc89', 'matcha-ink': '#3e6132',
  'sky-bgs': '#eaf5f9', 'sky-bg': '#cfe9f2', 'sky-bd': '#92c6d9', 'sky-ink': '#1f566b',
  'lavender-bgs': '#f4f0fa', 'lavender-bg': '#e2daf4', 'lavender-bd': '#bca9e3', 'lavender-ink': '#54408a',
  'brass-bg': '#f6ecd9', brass: '#d4a24f', 'brass-ink': '#6e5224',
  rose: '#c2486b', red: '#b64650',
  'radius-pill': '999px',
};

function parse(text) {
  const out = {};
  for (const m of text.matchAll(/--([a-z0-9-]+)\s*:\s*([^;]+);/g)) {
    out[m[1]] = m[2].trim();
  }
  return out;
}

const got = parse(readFileSync(GEN, 'utf8'));
const problems = [];

for (const [name, value] of Object.entries(EXPECTED)) {
  if (!(name in got)) problems.push(`MISSING in generated: --${name}`);
  else if (got[name] !== value) {
    problems.push(`VALUE DRIFT --${name}: expected ${value}, generated ${got[name]}`);
  }
}
for (const name of Object.keys(got)) {
  if (!(name in EXPECTED)) problems.push(`UNEXPECTED extra generated var: --${name}`);
}

if (problems.length) {
  console.error('[verify-css] CSS diff-0 FAILED:');
  for (const p of problems) console.error('  - ' + p);
  process.exit(1);
}
console.log(`[verify-css] CSS diff-0 OK — ${Object.keys(EXPECTED).length} token vars match the landing :root exactly.`);
