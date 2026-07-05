import { dirname } from "path";
import { fileURLToPath } from "url";
import { FlatCompat } from "@eslint/eslintrc";

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const compat = new FlatCompat({ baseDirectory: __dirname });

const config = [
  ...compat.extends("next/core-web-vitals", "next/typescript"),
  {
    rules: {
      // DS 이식성 위해 원시 img 허용(의도) — 경고로만.
      "@next/next/no-img-element": "warn",
      // a11y 품질 게이트(R5-W3 #7a) — 정적 요소 인터랙션/키보드 이벤트 누락은 error로 승격(회귀 차단).
      "jsx-a11y/no-static-element-interactions": "error",
      "jsx-a11y/click-events-have-key-events": "error",
      "@typescript-eslint/no-unused-vars": ["warn", { argsIgnorePattern: "^_", varsIgnorePattern: "^_" }],
      "@typescript-eslint/no-explicit-any": "warn",
    },
  },
  { ignores: [".next/**", "node_modules/**", "scripts/**", "**/*.config.*", "src/lib/api/schema.d.ts"] },
];

export default config;
