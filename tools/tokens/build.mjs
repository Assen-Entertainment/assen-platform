// Style Dictionary codegen for Assen Platform design tokens (ASS-128).
//
// WHY this file is hand-written but the OUTPUTS are generated:
//   The single source of truth is docs/design/tokens.json (W3C DTCG 2025.10,
//   OQ-11 — drift is not accepted). This script is the *projection rule*; the
//   files it writes carry a "DO NOT EDIT BY HAND (#32)" header and are proven
//   hand-edit-free by `melos run codegen:verify` (regenerate + git diff empty).
//
// TWO consumers, ONE source:
//   (A) Dart  -> packages/core_tokens/lib/src/*.gen.dart  (raw const + ThemeExtension)
//   (B) Vite  -> landing/src/tokens.generated.css         (:root custom properties)
//
// SPIKE NOTE (ASS-128, CSS diff-0 acceptance):
//   The EXISTING landing/src/style.css :root block predates tokens.json and uses
//   ad-hoc, abbreviated variable names (--strawberry-bgs, --brass, --rose, --red)
//   with lowercase hex. To honour "generated CSS == existing :root, diff 0" we
//   emit exactly that ad-hoc naming via CSS_NAME_MAP below (an explicit, auditable
//   projection table) and lowercase the hex. We emit ONLY the colour/radius tokens
//   that round-trip byte-identically. Non-token landing-locals (--gutter, fonts,
//   --shadow-* as rgba) stay in style.css OUTSIDE the generated block. The three
//   real source drifts surfaced by this spike (shadow alpha 0x14≈0.078 vs 0.08,
//   the absent --peach-bgs, font-family "Cafe24 Ssurround" vs 'Cafe24Ssurround')
//   are reported as findings, NOT silently reconciled. See ADR-0004.

import StyleDictionary from 'style-dictionary';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';

const __dirname = dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = resolve(__dirname, '..', '..');
const TOKENS_SRC = resolve(REPO_ROOT, 'docs/design/tokens.json');

const GEN_HEADER_LINES = [
  'GENERATED — DO NOT EDIT BY HAND (#32).',
  'Source: docs/design/tokens.json (W3C DTCG 2025.10).',
  'Regenerate: dart run melos run codegen   (verify: melos run codegen:verify).',
];

// ---------------------------------------------------------------------------
// CSS projection table: DTCG token path  ->  existing ad-hoc :root var name.
// Order here defines the emit order so the generated block matches style.css.
// Only tokens whose VALUE round-trips byte-identically are listed; deliberately
// excludes peach.bgSubtle (absent in source CSS — documented drift), shadows,
// fonts and --gutter (landing-locals).
// ---------------------------------------------------------------------------
const CSS_NAME_MAP = [
  // color.ref — creams + white
  ['color.ref.cream.50', 'cream-50'],
  ['color.ref.cream.100', 'cream-100'],
  ['color.ref.cream.200', 'cream-200'],
  ['color.ref.cream.300', 'cream-300'],
  ['color.ref.white', 'white'],
  // ink ramp
  ['color.ref.ink.900', 'ink-900'],
  ['color.ref.ink.700', 'ink-700'],
  ['color.ref.ink.500', 'ink-500'],
  ['color.ref.ink.300', 'ink-300'],
  ['color.ref.ink.200', 'ink-200'],
  ['color.ref.ink.100', 'ink-100'],
  // pastel hues (bgSubtle->bgs, bg, border->bd, ink). peach.bgSubtle intentionally omitted.
  ['color.ref.strawberry.bgSubtle', 'strawberry-bgs'],
  ['color.ref.strawberry.bg', 'strawberry-bg'],
  ['color.ref.strawberry.border', 'strawberry-bd'],
  ['color.ref.strawberry.ink', 'strawberry-ink'],
  ['color.ref.peach.bg', 'peach-bg'],
  ['color.ref.peach.border', 'peach-bd'],
  ['color.ref.peach.ink', 'peach-ink'],
  ['color.ref.lemon.bgSubtle', 'lemon-bgs'],
  ['color.ref.lemon.bg', 'lemon-bg'],
  ['color.ref.lemon.border', 'lemon-bd'],
  ['color.ref.lemon.ink', 'lemon-ink'],
  ['color.ref.matcha.bgSubtle', 'matcha-bgs'],
  ['color.ref.matcha.bg', 'matcha-bg'],
  ['color.ref.matcha.border', 'matcha-bd'],
  ['color.ref.matcha.ink', 'matcha-ink'],
  ['color.ref.sky.bgSubtle', 'sky-bgs'],
  ['color.ref.sky.bg', 'sky-bg'],
  ['color.ref.sky.border', 'sky-bd'],
  ['color.ref.sky.ink', 'sky-ink'],
  ['color.ref.lavender.bgSubtle', 'lavender-bgs'],
  ['color.ref.lavender.bg', 'lavender-bg'],
  ['color.ref.lavender.border', 'lavender-bd'],
  ['color.ref.lavender.ink', 'lavender-ink'],
  // brass / brand / state
  ['color.ref.brass.bg', 'brass-bg'],
  ['color.ref.brass.main', 'brass'],
  ['color.ref.brass.ink', 'brass-ink'],
  ['color.ref.rose.main', 'rose'],
  ['color.ref.red.main', 'red'],
  // radius.full -> --radius-pill (only radius token present in :root)
  ['radius.full', 'radius-pill'],
];

// Look up a flattened token by its dotted DTCG path.
function tokenByPath(dictionary, path) {
  return dictionary.allTokens.find((t) => t.path.join('.') === path);
}

// Render a token's CSS text. Under `usesDtcg` + the `css` transformGroup, SD has
// already lowercased colours and rendered dimensions ("999px") into `$value`,
// so the generated block matches the existing lowercase ad-hoc :root byte-for-byte.
function cssValue(token) {
  return String(token.$value);
}

// ---------------------------------------------------------------------------
// Custom CSS format: emit the ad-hoc :root subset, diff-0 against style.css.
// ---------------------------------------------------------------------------
StyleDictionary.registerFormat({
  name: 'assen/css-vite',
  format: ({ dictionary }) => {
    const head = GEN_HEADER_LINES.map((l) => ` * ${l}`).join('\n');
    const lines = CSS_NAME_MAP.map(([path, name]) => {
      const tok = tokenByPath(dictionary, path);
      if (!tok) throw new Error(`CSS map: token not found for path ${path}`);
      return `  --${name}: ${cssValue(tok)};`;
    });
    return `/*\n${head}\n */\n:root {\n${lines.join('\n')}\n}\n`;
  },
});

// ---------------------------------------------------------------------------
// Dart helpers
// ---------------------------------------------------------------------------
const dartDocHeader = () =>
  GEN_HEADER_LINES.map((l) => `// ${l}`).join('\n');

// Pristine DTCG primitive (uppercase hex, numeric dimensions) for the Dart side.
// `token.$value` is transformed by the platform group; `original.$value` is not.
function rawValue(token) {
  return token.original.$value;
}

// 0xAARRGGBB from a #RRGGBB or #RRGGBBAA hex string (DTCG colours).
function dartColorLiteral(hex) {
  const h = hex.replace('#', '');
  let r, g, b, a;
  if (h.length === 6) {
    a = 'ff';
    r = h.slice(0, 2); g = h.slice(2, 4); b = h.slice(4, 6);
  } else if (h.length === 8) {
    // DTCG hex8 is #RRGGBBAA
    r = h.slice(0, 2); g = h.slice(2, 4); b = h.slice(4, 6); a = h.slice(6, 8);
  } else {
    throw new Error(`Unexpected hex length: ${hex}`);
  }
  return `Color(0x${(a + r + g + b).toUpperCase()})`;
}

const dartConstName = (path) =>
  // color.ref.strawberry.bgSubtle -> strawberryBgSubtle ; drop the color.ref prefix
  path
    .replace(/^color\.ref\./, '')
    .replace(/^color\.sys\./, '')
    .split('.')
    .map((seg, i) => (i === 0 ? seg : seg[0].toUpperCase() + seg.slice(1)))
    .join('')
    .replace(/[^A-Za-z0-9]/g, '');

function buildColorsDart(dictionary) {
  const refs = dictionary.allTokens.filter(
    (t) => t.path[0] === 'color' && t.path[1] === 'ref' && (t.$type ?? t.type) === 'color',
  );
  const fields = refs
    .map((t) => {
      const name = dartConstName(t.path.join('.'));
      const desc = t.$description ?? t.description;
      const doc = desc ? `  /// ${desc}\n` : '';
      return `${doc}  static const Color ${name} = ${dartColorLiteral(String(rawValue(t)))};`;
    })
    .join('\n\n');
  return `${dartDocHeader()}

import 'dart:ui';

/// Raw reference colour ramp (color.ref.*) from the design token source.
///
/// These are primitives only — semantic M3 roles (color.sys.*) and the
/// ColorScheme are deliberately NOT generated (a seeded M3 scheme distorts the
/// cream surface; see docs/design/tokens.md and ADR-0004). Consume these via
/// [AssenColors] (ThemeExtension) or directly for decorative motifs.
abstract final class RefColors {
${fields}
}
`;
}

function buildSpacingDart(dictionary) {
  const items = dictionary.allTokens.filter((t) => t.path[0] === 'spacing');
  const fields = items
    .map((t) => {
      const key = t.path[1];
      const name = /^[0-9]/.test(key) ? `s${key}` : key;
      const v = rawValue(t).value;
      const desc = t.$description ?? t.description;
      const doc = desc ? `  /// ${desc}\n` : `  /// spacing.${key} — ${v}px on the 4dp grid.\n`;
      return `${doc}  static const double ${name} = ${v};`;
    })
    .join('\n\n');
  return `${dartDocHeader()}

/// Spacing scale (spacing.*) in logical pixels. 4dp base grid.
abstract final class SpacingTokens {
${fields}
}
`;
}

function buildRadiusDart(dictionary) {
  const items = dictionary.allTokens.filter((t) => t.path[0] === 'radius');
  const fields = items
    .map((t) => {
      const key = t.path[1];
      const v = rawValue(t).value;
      const desc = t.$description ?? t.description;
      const doc = desc ? `  /// ${desc}\n` : `  /// radius.${key} — ${v}px.\n`;
      return `${doc}  static const double ${key} = ${v};`;
    })
    .join('\n\n');
  return `${dartDocHeader()}

/// Corner radius scale (radius.*) in logical pixels.
abstract final class RadiusTokens {
${fields}
}
`;
}

function buildElevationDart(dictionary) {
  const items = dictionary.allTokens.filter((t) => t.path[0] === 'elevation');
  // Each elevation is a DTCG shadow object. Emit colour + offsets + blur as raw
  // primitives so ui_kit can assemble BoxShadow without re-reading the source.
  const fields = items
    .map((t) => {
      const key = t.path[1];
      const s = rawValue(t);
      const cap = key[0].toUpperCase() + key.slice(1);
      const desc = t.$description ?? t.description;
      const doc = desc ? `  /// ${desc}\n` : '';
      return (
        `${doc}  static const Color ${key}Color = ${dartColorLiteral(s.color)};\n` +
        `  static const double ${key}OffsetX = ${s.offsetX.value};\n` +
        `  static const double ${key}OffsetY = ${s.offsetY.value};\n` +
        `  static const double ${key}Blur = ${s.blur.value};\n` +
        `  static const double ${key}Spread = ${s.spread.value};`
      );
    })
    .join('\n\n');
  return `${dartDocHeader()}

import 'dart:ui';

/// Elevation shadow primitives (elevation.*). level0 has no shadow (outline
/// only); these are level1 (cards) and level2 (sheets/dialogs).
abstract final class ElevationTokens {
${fields}
}
`;
}

function buildMotionDart(dictionary) {
  const durs = dictionary.allTokens.filter(
    (t) => t.path[0] === 'motion' && t.path[1] === 'duration',
  );
  const fields = durs
    .map((t) => {
      const key = t.path[2];
      const ms = rawValue(t).value;
      const desc = t.$description ?? t.description;
      const doc = desc ? `  /// ${desc}\n` : `  /// motion.duration.${key} — ${ms}ms.\n`;
      return `${doc}  static const Duration ${key} = Duration(milliseconds: ${ms});`;
    })
    .join('\n\n');
  return `${dartDocHeader()}

/// Motion duration primitives (motion.duration.*).
abstract final class MotionDurations {
${fields}
}
`;
}

// ---------------------------------------------------------------------------
// Typography (ASS-130). The `typography.*` block is the SSOT mirror of
// docs/design/tokens.md §3. We emit THREE primitive groups so ui_kit can drop
// its placeholder `_*Size` literals onto a generated source:
//   (1) fontSize doubles  (logical px) — the value ui_kit was hard-coding,
//   (2) fontFamily primary + fallback lists (Flutter wants a primary String
//       plus a fontFamilyFallback list),
//   (3) a composed TextStyle per scale slot (family + size + height + weight),
//       offered for new code; existing widgets that only need the size keep
//       their own weight/height by reading the `*Size` const.
// Values are read from `original.$value` (pristine DTCG) so SD reference
// resolution / unit transforms never perturb the generated numbers.
// ---------------------------------------------------------------------------

// camelCase a fontFamily reference `{typography.fontFamily.display}` -> `display`.
function familyKeyFromRef(ref) {
  const m = /^\{typography\.fontFamily\.([^}]+)\}$/.exec(String(ref));
  if (!m) throw new Error(`typography: unexpected fontFamily ref ${ref}`);
  return m[1];
}

// Dart `FontWeight.wNNN` from a numeric DTCG fontWeight (100..900).
function dartFontWeight(w) {
  return `FontWeight.w${w}`;
}

// A Dart `const List<String>` field, emitted the way `dart format` would: the
// inline form `[ 'a', 'b' ]` when the whole declaration fits in 80 columns, else
// one element per line with a trailing comma. Keeping the generator output
// format-stable is required — `melos run format` and `codegen:verify` both run
// over the *.gen.dart, so an unformatted emit would fail CI / drift the diff.
function dartStringListField(indent, decl, items) {
  const inlineItems = items.map((s) => `'${s}'`).join(', ');
  const inline = `${indent}${decl} = [${inlineItems}];`;
  if (inline.length <= 80) return inline;
  const lines = items.map((s) => `${indent}  '${s}',`).join('\n');
  return `${indent}${decl} = [\n${lines}\n${indent}];`;
}

function buildTypographyDart(dictionary) {
  const families = dictionary.allTokens.filter(
    (t) => t.path[0] === 'typography' && t.path[1] === 'fontFamily',
  );
  const scales = dictionary.allTokens.filter(
    (t) => t.path[0] === 'typography' && t.path[1] === 'scale',
  );

  const familyFields = families
    .map((t) => {
      const key = t.path[2];
      const stack = rawValue(t);
      if (!Array.isArray(stack) || stack.length === 0) {
        throw new Error(`typography: fontFamily.${key} is not a non-empty list`);
      }
      const primary = stack[0];
      const fallback = stack.slice(1);
      const fallbackField = dartStringListField(
        '  ',
        `static const List<String> ${key}FontFamilyFallback`,
        fallback,
      );
      return (
        `  /// typography.fontFamily.${key} — primary face.\n` +
        `  static const String ${key}FontFamily = '${primary}';\n\n` +
        `  /// typography.fontFamily.${key} — fallback stack (after the primary).\n` +
        `${fallbackField}`
      );
    })
    .join('\n\n');

  const sizeFields = scales
    .map((t) => {
      const key = t.path[2];
      const v = rawValue(t);
      const size = v.fontSize.value;
      return `  /// typography.scale.${key} — ${size}px.\n` +
        `  static const double ${key}Size = ${size};`;
    })
    .join('\n\n');

  const styleFields = scales
    .map((t) => {
      const key = t.path[2];
      const v = rawValue(t);
      const famKey = familyKeyFromRef(v.fontFamily);
      const size = v.fontSize.value;
      const height = v.lineHeight;
      const weight = dartFontWeight(v.fontWeight);
      return (
        `  /// typography.scale.${key} — composed ${famKey} ${size}px style.\n` +
        `  static const TextStyle ${key} = TextStyle(\n` +
        `    fontFamily: ${famKey}FontFamily,\n` +
        `    fontFamilyFallback: ${famKey}FontFamilyFallback,\n` +
        `    fontSize: ${size},\n` +
        `    height: ${height},\n` +
        `    fontWeight: ${weight},\n` +
        `  );`
      );
    })
    .join('\n\n');

  return `${dartDocHeader()}

import 'package:flutter/painting.dart';

/// Typography primitives (typography.*) — SSOT mirror of docs/design/tokens.md
/// §3. Font sizes are in logical pixels; [TextStyle] composites pair each scale
/// slot with its family stack, line height and weight. Widgets that only need a
/// size read \`*Size\`; new code can take the whole composed style.
abstract final class TypographyTokens {
${familyFields}

${sizeFields}

${styleFields}
}
`;
}

// ThemeExtensions: thin, generated wrappers exposing the raw const groups to the
// Flutter theme. These are PRIMITIVES surfaced for `Theme.of(context).extension`,
// not the semantic ColorScheme (which stays hand-written in ui_kit).
function buildThemeExtensionsDart(dictionary) {
  const refs = dictionary.allTokens.filter(
    (t) => t.path[0] === 'color' && t.path[1] === 'ref' && (t.$type ?? t.type) === 'color',
  );
  const colorFields = refs.map((t) => `  final Color ${dartConstName(t.path.join('.'))};`).join('\n');
  const colorCtor = refs
    .map((t) => {
      const n = dartConstName(t.path.join('.'));
      return `    this.${n} = RefColors.${n},`;
    })
    .join('\n');
  const colorLerpReturn = refs
    .map((t) => `      ${dartConstName(t.path.join('.'))}: other.${dartConstName(t.path.join('.'))},`)
    .join('\n');
  const colorCopyParams = refs.map((t) => `    Color? ${dartConstName(t.path.join('.'))},`).join('\n');
  const colorCopyAssign = refs
    .map((t) => {
      const n = dartConstName(t.path.join('.'));
      return `      ${n}: ${n} ?? this.${n},`;
    })
    .join('\n');

  return `${dartDocHeader()}

import 'package:flutter/material.dart';

import 'colors.gen.dart';
import 'radius.gen.dart';
import 'spacing.gen.dart';

/// Raw reference colours exposed as a [ThemeExtension].
///
/// Read with \`Theme.of(context).extension<AssenColors>()\`. Defaults mirror
/// [RefColors]; a dark ramp can be added later by passing overrides. The
/// semantic ColorScheme is NOT here — it is hand-mapped in ui_kit.
final class AssenColors extends ThemeExtension<AssenColors> {
  const AssenColors({
${colorCtor}
  });

${colorFields}

  @override
  AssenColors copyWith({
${colorCopyParams}
  }) {
    return AssenColors(
${colorCopyAssign}
    );
  }

  /// Colours are discrete brand primitives; lerp snaps to [other] at t >= 0.5
  /// rather than interpolating (no meaningful in-between brand colour).
  @override
  AssenColors lerp(ThemeExtension<AssenColors>? other, double t) {
    if (other is! AssenColors || t < 0.5) return this;
    return AssenColors(
${colorLerpReturn}
    );
  }
}

/// Spacing scale exposed as a [ThemeExtension]. Values come from [SpacingTokens].
final class AssenSpacing extends ThemeExtension<AssenSpacing> {
  const AssenSpacing();

  /// 16px — the most common gutter (spacing.4).
  double get md => SpacingTokens.s4;

  @override
  AssenSpacing copyWith() => const AssenSpacing();

  @override
  AssenSpacing lerp(ThemeExtension<AssenSpacing>? other, double t) => this;
}

/// Corner radii exposed as a [ThemeExtension]. Values come from [RadiusTokens].
final class AssenRadius extends ThemeExtension<AssenRadius> {
  const AssenRadius();

  /// Card radius (radius.lg = 16px).
  double get card => RadiusTokens.lg;

  @override
  AssenRadius copyWith() => const AssenRadius();

  @override
  AssenRadius lerp(ThemeExtension<AssenRadius>? other, double t) => this;
}
`;
}

// ---------------------------------------------------------------------------
// File-writing format wrappers (Style Dictionary "file.format" hooks).
// We register one format per Dart file so SD owns the write + cleanPlatform.
// ---------------------------------------------------------------------------
const dartFormats = {
  'assen/dart-colors': buildColorsDart,
  'assen/dart-spacing': buildSpacingDart,
  'assen/dart-radius': buildRadiusDart,
  'assen/dart-elevation': buildElevationDart,
  'assen/dart-motion': buildMotionDart,
  'assen/dart-typography': buildTypographyDart,
  'assen/dart-theme-extensions': buildThemeExtensionsDart,
};
for (const [name, fn] of Object.entries(dartFormats)) {
  StyleDictionary.registerFormat({ name, format: ({ dictionary }) => fn(dictionary) });
}

// ---------------------------------------------------------------------------
// Run
// ---------------------------------------------------------------------------
const sd = new StyleDictionary({
  source: [TOKENS_SRC],
  // tokens.json is DTCG ($type/$value); tell SD to parse + emit in that dialect.
  usesDtcg: true,
  platforms: {
    css: {
      transformGroup: 'css',
      buildPath: resolve(REPO_ROOT, 'landing/src') + '/',
      files: [{ destination: 'tokens.generated.css', format: 'assen/css-vite' }],
    },
    dart: {
      transformGroup: 'js',
      buildPath: resolve(REPO_ROOT, 'packages/core_tokens/lib/src') + '/',
      files: [
        { destination: 'colors.gen.dart', format: 'assen/dart-colors' },
        { destination: 'spacing.gen.dart', format: 'assen/dart-spacing' },
        { destination: 'radius.gen.dart', format: 'assen/dart-radius' },
        { destination: 'elevation.gen.dart', format: 'assen/dart-elevation' },
        { destination: 'motion.gen.dart', format: 'assen/dart-motion' },
        { destination: 'typography.gen.dart', format: 'assen/dart-typography' },
        { destination: 'theme_extensions.gen.dart', format: 'assen/dart-theme-extensions' },
      ],
    },
  },
});

await sd.cleanAllPlatforms();
await sd.buildAllPlatforms();
console.log('[assen codegen] wrote Dart (packages/core_tokens) + CSS (landing/src).');
