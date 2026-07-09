import { dirname } from "path";
import { fileURLToPath } from "url";
import { FlatCompat } from "@eslint/eslintrc";
import jsxA11y from "eslint-plugin-jsx-a11y";

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const compat = new FlatCompat({ baseDirectory: __dirname });

const config = [
  ...compat.extends("next/core-web-vitals", "next/typescript"),
  {
    // jsx-a11y recommended 전면(품질 고도화) — next/core-web-vitals가 이미 "jsx-a11y" 플러그인을
    // 등록해두므로(FlatCompat 변환) 여기선 규칙 세트만 병합한다. flatConfigs.recommended 객체를
    // 통째로 스프레드하면 plugins 필드가 다른 모듈 인스턴스로 중복 등록되어 ESLint가
    // "Cannot redefine plugin" 오류를 던진다 — rules만 취해 이미 등록된 플러그인에 위임.
    rules: {
      ...jsxA11y.flatConfigs.recommended.rules,
      // DS 이식성 위해 원시 img 허용(의도) — 경고로만.
      "@next/next/no-img-element": "warn",
      // a11y 품질 게이트(R5-W3 #7a) — 정적 요소 인터랙션/키보드 이벤트 누락은 error로 승격(회귀 차단).
      "jsx-a11y/no-static-element-interactions": "error",
      "jsx-a11y/click-events-have-key-events": "error",
      // Calendar의 `autoFocus` prop은 커스텀 컴포넌트 prop(effect로 수동 focus() — 네이티브
      // DOM autofocus 속성이 아님). ignoreNonDOM으로 실제 DOM 엘리먼트만 검사 대상 유지.
      "jsx-a11y/no-autofocus": ["error", { ignoreNonDOM: true }],
      "@typescript-eslint/no-unused-vars": ["warn", { argsIgnorePattern: "^_", varsIgnorePattern: "^_" }],
      "@typescript-eslint/no-explicit-any": "warn",
    },
  },
  { ignores: [".next/**", "node_modules/**", "scripts/**", "**/*.config.*", "src/lib/api/schema.d.ts", "**/*.stories.tsx", ".storybook/**", "storybook-static/**"] },
];

export default config;
