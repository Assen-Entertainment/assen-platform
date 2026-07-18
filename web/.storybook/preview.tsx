import * as React from "react";
import type { Preview } from "@storybook/nextjs";
import { INITIAL_VIEWPORTS } from "storybook/viewport";
import "../src/styles/globals.css";

/**
 * 전역 프리뷰 — 디자인 토큰(globals.css) 로드 + 라이트/다크 토글 + 뷰포트 + a11y.
 * 다크모드: 갤러리(app/gallery)와 동일하게 <html class="dark"> 토글(토큰이 :root/.dark 로 정의됨).
 *  포털(Dialog/Sheet/Tooltip/Toast 등)이 document.body 에 렌더되므로 wrapper 가 아닌 documentElement 에 적용해야
 *  오버레이도 테마를 따른다.
 */
const preview: Preview = {
  // 전 컴포넌트 자동 문서(Docs) 페이지 생성.
  tags: ["autodocs"],
  parameters: {
    layout: "padded",
    controls: {
      matchers: { color: /(background|color)$/i, date: /Date$/i },
      expanded: true,
    },
    // 토큰 surface 를 캔버스 배경으로 쓰므로 Storybook backgrounds 는 비활성.
    backgrounds: { disable: true },
    a11y: {
      // 위반을 패널에 리포트하되 빌드는 실패시키지 않음(심각분만 수정, 구조변경분은 보고).
      test: "todo",
    },
    viewport: {
      options: {
        mobile: { name: "Mobile · 375", styles: { width: "375px", height: "812px" }, type: "mobile" },
        tablet: { name: "Tablet · 768", styles: { width: "768px", height: "1024px" }, type: "tablet" },
        desktop: { name: "Desktop · 1280", styles: { width: "1280px", height: "800px" }, type: "desktop" },
        ...INITIAL_VIEWPORTS,
      },
    },
  },
  initialGlobals: {
    theme: "light",
  },
  globalTypes: {
    theme: {
      description: "라이트/다크 테마 토글",
      toolbar: {
        title: "Theme",
        icon: "contrast",
        items: [
          { value: "light", title: "라이트", icon: "sun" },
          { value: "dark", title: "다크", icon: "moon" },
        ],
        dynamicTitle: true,
      },
    },
  },
  decorators: [
    (Story, context) => {
      const theme = (context.globals.theme as string) ?? "light";
      React.useEffect(() => {
        const root = document.documentElement;
        root.classList.toggle("dark", theme === "dark");
        // 캔버스 전체(포털 포함)가 토큰 surface 를 따르도록 body 배경/잉크 동기화.
        document.body.style.backgroundColor = "var(--surface)";
        document.body.style.color = "var(--on-surface)";
      }, [theme]);
      return <Story />;
    },
  ],
};

export default preview;
