import * as React from "react";
import { WebShell } from "@/components/shell/web-shell";

/** (main) 라우트 그룹 — 웹 셸(Sidebar+TopBar) 공유. */
export default function MainLayout({ children }: { children: React.ReactNode }) {
  return <WebShell>{children}</WebShell>;
}
