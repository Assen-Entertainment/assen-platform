import type { StorybookConfig } from "@storybook/nextjs";

/**
 * Storybook — Assen 웹 디자인시스템 발행(ASS-158 / R7).
 * framework=@storybook/nextjs(webpack5): vite@7·vitest@4 툴체인과 완전 격리(무회귀).
 *  - tsconfig paths(@/*) 자동 해석, next/font·next/image·next/link 목킹, postcss(@tailwindcss/postcss v4) 파이프라인 재사용.
 * 정적 발행: `npm run build-storybook` → storybook-static/(호스팅 하네스는 E10 게이트).
 */
const config: StorybookConfig = {
  stories: ["../src/**/*.mdx", "../src/**/*.stories.@(ts|tsx)"],
  // addon-docs: 컴포넌트별 자동 문서(Docs) 페이지(prop 테이블) — preview.tsx 의 tags:["autodocs"] 와 짝.
  addons: ["@storybook/addon-docs", "@storybook/addon-a11y"],
  framework: {
    name: "@storybook/nextjs",
    options: {},
  },
  // public/fonts/pretendard-variable.woff2 를 /fonts/... 로 서빙(preview-head.html @font-face).
  staticDirs: ["../public"],
  // 스토리 전용 — react-docgen(경량·견고). 컨트롤은 각 스토리의 argTypes 로 명시.
  typescript: {
    reactDocgen: "react-docgen",
  },
};

export default config;
