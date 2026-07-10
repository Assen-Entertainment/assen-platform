import * as React from "react";
import type { Metadata } from "next";

// page.tsx는 "use client"라 metadata export 불가 — 검색 노출 제외(noindex)만을 위한 서버 레이아웃.
export const metadata: Metadata = {
  robots: { index: false, follow: false },
};

export default function GalleryLayout({ children }: { children: React.ReactNode }) {
  return children;
}
