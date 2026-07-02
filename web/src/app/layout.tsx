import type { Metadata } from "next";
import type { ReactNode } from "react";
import "@/styles/globals.css";
import { config } from "@/lib/config";
import { QueryProvider } from "@/components/query-provider";
import { Toaster } from "@/components/ui/use-toast";

export const metadata: Metadata = {
  metadataBase: new URL(config.siteUrl),
  title: { default: "Assen — 크리에이터 플랫폼", template: "%s · Assen" },
  description: "크리에이터의 세계관을 팬과 가장 가깝게 잇는, 믿을 수 있는 무대.",
  openGraph: { title: "Assen", description: "크리에이터-팬 플랫폼", type: "website", locale: "ko_KR" },
  twitter: { card: "summary_large_image" },
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="ko" suppressHydrationWarning>
      <body>
        <QueryProvider>
          <Toaster>{children}</Toaster>
        </QueryProvider>
      </body>
    </html>
  );
}
