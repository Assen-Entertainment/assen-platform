"use client";
import * as React from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { Sidebar, TopBar, SearchField, Button, Avatar, BottomNav } from "@/components/ui";
import { HomeIcon, FeedIcon, StoreIcon, HeartIcon, BellIcon, PersonIcon, SunIcon, MoonIcon } from "@/lib/icons";
import { useTheme } from "@/components/theme-provider";
import { useSession } from "@/lib/session";

/** Sidebar(lg+) 네비. 홈 다음에 피드(/feed) 진입점. */
const NAV = [
  { icon: <HomeIcon />, label: "홈", href: "/discovery" },
  { icon: <FeedIcon />, label: "피드", href: "/feed" },
  { icon: <StoreIcon />, label: "스토어", href: "/store" },
  { icon: <HeartIcon />, label: "멤버십", href: "/membership" },
];
/** BottomNav(<lg) 네비 — 사이드바 항목 + 마이(홈/피드/스토어/멤버십/마이 5탭).
 *  ※Figma 4탭은 모바일 앱 기준 — 웹은 피드 진입점을 노출해 5탭으로 의도적 편차. */
const BOTTOM_NAV = [...NAV, { icon: <PersonIcon />, label: "마이", href: "/mypage" }];

/** 테마 토글(해/달) — 하이드레이션 후에만 아이콘 결정(SSR 불일치 방지). */
function ThemeToggle() {
  const { resolvedTheme, setTheme, mounted } = useTheme();
  const isDark = resolvedTheme === "dark";
  return (
    <button
      type="button"
      aria-label={isDark ? "라이트 모드로 전환" : "다크 모드로 전환"}
      onClick={() => setTheme(isDark ? "light" : "dark")}
      className="flex size-9 items-center justify-center rounded-full text-on-surface-variant transition-colors hover:bg-surface-container-high [&>svg]:size-5"
    >
      {mounted ? (isDark ? <SunIcon /> : <MoonIcon />) : <span className="size-5" aria-hidden />}
    </button>
  );
}

export function WebShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname() || "";
  const router = useRouter();
  const { user } = useSession();
  const [q, setQ] = React.useState("");
  const active = BOTTOM_NAV.find((n) => pathname.startsWith(n.href))?.href;
  const initial = user ? user.name.slice(0, 1) : "나";

  const onSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const query = q.trim();
    if (query) router.push(`/search?q=${encodeURIComponent(query)}`);
  };

  return (
    <div className="flex min-h-screen bg-surface">
      {/* 건너뛰기 링크(루브릭 #51) — 키보드 포커스 시에만 노출, 본문으로 이동. */}
      <a
        href="#main"
        className="sr-only z-[70] rounded-md bg-primary px-4 py-2 text-label text-on-primary focus:not-sr-only focus:fixed focus:left-4 focus:top-4"
      >
        본문으로 건너뛰기
      </a>
      <Sidebar
        className="hidden lg:flex"
        brand={<span className="text-title-l text-primary">Assen</span>}
        items={NAV}
        activeHref={active}
        footer={
          <Button className="w-full" asChild>
            <Link href="/studio">크리에이터 스튜디오</Link>
          </Button>
        }
      />
      <div className="flex min-w-0 flex-1 flex-col">
        <TopBar
          className="px-4 sm:px-6"
          logo={
            <Link href="/discovery" className="text-title-l text-primary lg:hidden">
              Assen
            </Link>
          }
          search={
            <form onSubmit={onSearchSubmit} className="w-full max-w-md" role="search">
              <SearchField
                name="q"
                value={q}
                onChange={(e) => setQ(e.target.value)}
                placeholder="크리에이터·상품 검색"
                aria-label="검색"
              />
            </form>
          }
          actions={
            <>
              <ThemeToggle />
              <Link
                href="/notifications"
                aria-label="알림"
                className="flex size-9 items-center justify-center rounded-full text-on-surface-variant transition-colors hover:bg-surface-container-high [&>svg]:size-5"
              >
                <BellIcon />
              </Link>
              <Link href="/mypage" aria-label="내 페이지">
                <Avatar fallback={initial} size="sm" />
              </Link>
            </>
          }
        />
        <main id="main" className="flex-1 overflow-auto p-4 pb-20 sm:p-6 lg:pb-6">{children}</main>
      </div>
      <BottomNav
        className="fixed inset-x-0 bottom-0 z-40 lg:hidden"
        items={BOTTOM_NAV}
        activeHref={active}
      />
    </div>
  );
}
