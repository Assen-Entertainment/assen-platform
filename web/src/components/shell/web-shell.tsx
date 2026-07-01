"use client";
import * as React from "react";
import { usePathname } from "next/navigation";
import { Sidebar, TopBar, SearchField, Button, Avatar } from "@/components/ui";
import { HomeIcon, StoreIcon, HeartIcon, BellIcon } from "@/lib/icons";

const NAV = [
  { icon: <HomeIcon />, label: "홈", href: "/discovery" },
  { icon: <StoreIcon />, label: "스토어", href: "/store" },
  { icon: <HeartIcon />, label: "멤버십", href: "/membership" },
];

export function WebShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname() || "";
  const active = NAV.find((n) => pathname.startsWith(n.href))?.href;
  return (
    <div className="flex min-h-screen bg-surface">
      <Sidebar
        brand={<span className="text-title-l text-primary">Assen</span>}
        items={NAV}
        activeHref={active}
        footer={<Button className="w-full">크리에이터 스튜디오</Button>}
      />
      <div className="flex min-w-0 flex-1 flex-col">
        <TopBar
          search={<SearchField className="w-full max-w-md" placeholder="크리에이터·상품 검색" />}
          actions={
            <>
              <button
                aria-label="알림"
                className="flex size-9 items-center justify-center rounded-full text-on-surface-variant hover:bg-surface-container-high [&>svg]:size-5"
              >
                <BellIcon />
              </button>
              <Avatar fallback="나" size="sm" />
            </>
          }
        />
        <main className="flex-1 overflow-auto p-6">{children}</main>
      </div>
    </div>
  );
}
