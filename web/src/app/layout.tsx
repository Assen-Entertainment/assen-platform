import type { Metadata } from "next";
import type { ReactNode } from "react";
import localFont from "next/font/local";
import "@/styles/globals.css";
import { config } from "@/lib/config";
import { QueryProvider } from "@/components/query-provider";
import { ThemeProvider, THEME_INIT_SCRIPT } from "@/components/theme-provider";
import { SessionProvider } from "@/lib/session";
import { SessionGuard } from "@/components/session-guard";
import { AnalyticsRouteTracker } from "@/components/analytics-route-tracker";
import { MotionProvider } from "@/components/motion-provider";
import { Toaster } from "@/components/ui/use-toast";

/** Pretendard Variable — 자체 호스팅(next/font/local, FOIT 방지 display:swap). CSS 변수로 노출. */
const pretendard = localFont({
  src: "../../public/fonts/pretendard-variable.woff2",
  variable: "--font-pretendard",
  display: "swap",
  weight: "45 920",
});

export const metadata: Metadata = {
  metadataBase: new URL(config.siteUrl),
  title: { default: "Assen — 크리에이터 플랫폼", template: "%s · Assen" },
  description: "크리에이터의 세계관을 팬과 가장 가깝게 잇는, 믿을 수 있는 무대.",
  openGraph: { title: "Assen", description: "크리에이터-팬 플랫폼", type: "website", locale: "ko_KR" },
  twitter: { card: "summary_large_image" },
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="ko" className={pretendard.variable} suppressHydrationWarning>
      <head>
        {/* FOUC 방지 — 하이드레이션 전 테마 적용(theme-provider.THEME_INIT_SCRIPT). */}
        <script dangerouslySetInnerHTML={{ __html: THEME_INIT_SCRIPT }} />
      </head>
      <body>
        <ThemeProvider>
          {/* QueryProvider가 SessionProvider 바깥 — 세션이 React Query(['auth','me'])를 사용. */}
          <QueryProvider>
            <SessionProvider>
              <Toaster>
                <SessionGuard />
                <AnalyticsRouteTracker />
                <MotionProvider>{children}</MotionProvider>
              </Toaster>
            </SessionProvider>
          </QueryProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
