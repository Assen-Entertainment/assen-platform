"use client";
import * as React from "react";
import type { ReactNode } from "react";
import { useRouter } from "next/navigation";
import { cn } from "@/lib/utils";
import { ListItem, EmptyState, ErrorState, Divider, Button, LoadMore } from "@/components/ui";
import { HeartFilledIcon, CommentIcon, PersonIcon, StoreIcon, BellIcon } from "@/lib/icons";
import { useNotifications, useMarkNotificationRead, useMarkAllNotificationsRead } from "@/lib/api/queries";
import type { Notification, NotificationKind, Page } from "@/lib/api";

const ICON: Record<NotificationKind, ReactNode> = {
  like: <HeartFilledIcon className="size-5 text-error" />,
  comment: <CommentIcon className="size-5 text-primary" />,
  follow: <PersonIcon className="size-5 text-primary" />,
  order: <StoreIcon className="size-5 text-on-surface-variant" />,
  system: <BellIcon className="size-5 text-on-surface-variant" />,
};

const GROUPS: { key: Notification["group"]; label: string }[] = [
  { key: "today", label: "오늘" },
  { key: "earlier", label: "이전" },
];

export function NotificationsView({ notifications }: { notifications: Page<Notification> }) {
  const router = useRouter();
  // USE_API면 실 목록/읽음, 아니면 mock(sleep) — 낙관적 read=true 반영.
  const { data, isError, refetch, fetchNextPage, hasNextPage, isFetchingNextPage } = useNotifications(notifications);
  const list = data ?? notifications.items;
  const markReadMut = useMarkNotificationRead();
  const markAllMut = useMarkAllNotificationsRead();

  const isRead = (n: Notification) => !!n.read;
  const open = (n: Notification) => {
    if (!n.read) markReadMut.mutate(n.id);
    // 내부 경로("/…")만 허용 — 외부 절대 URL·프로토콜은 오픈 리다이렉트 방지 위해 무시.
    if (n.href && n.href.startsWith("/")) router.push(n.href);
  };
  const markAll = () => markAllMut.mutate();
  const unread = list.filter((n) => !n.read).length;

  if (isError && !data) {
    return (
      <div className="mx-auto flex max-w-4xl flex-col gap-4">
        <h1 className="text-headline text-on-surface">알림</h1>
        <ErrorState onRetry={() => refetch()} />
      </div>
    );
  }

  if (!list.length) {
    return (
      <div className="mx-auto flex max-w-4xl flex-col gap-4">
        <h1 className="text-headline text-on-surface">알림</h1>
        <EmptyState title="알림이 없어요" description="새 소식이 오면 여기에 표시됩니다." />
      </div>
    );
  }

  return (
    <div className="mx-auto flex max-w-4xl flex-col gap-4">
      <div className="flex items-center justify-between">
        <h1 className="text-headline text-on-surface">알림</h1>
        {unread > 0 ? (
          <Button variant="ghost" size="sm" onClick={markAll}>
            모두 읽음
          </Button>
        ) : null}
      </div>
      {GROUPS.map((g) => {
        const items = list.filter((n) => n.group === g.key);
        if (!items.length) return null;
        return (
          <section key={g.key} className="flex flex-col gap-2">
            <h2 className="px-1 text-label text-on-surface-variant">{g.label}</h2>
            <div className="overflow-hidden rounded-lg border border-outline">
              {items.map((n, i) => (
                <div key={n.id}>
                  {i > 0 ? <Divider /> : null}
                  <button
                    type="button"
                    onClick={() => open(n)}
                    className={cn(
                      "block w-full text-left transition-colors hover:bg-surface-container-high",
                      !isRead(n) && "bg-primary-container/30",
                    )}
                  >
                    <ListItem
                      leading={
                        <span className="relative flex size-9 items-center justify-center rounded-full bg-surface-container-high">
                          {ICON[n.kind]}
                          {!isRead(n) ? (
                            <span className="absolute -right-0.5 -top-0.5 size-2.5 rounded-full border-2 border-surface bg-primary" />
                          ) : null}
                        </span>
                      }
                      title={n.title}
                      subtitle={n.time}
                      showChevron
                    />
                  </button>
                </div>
              ))}
            </div>
          </section>
        );
      })}
      {/* 무한 스크롤 sentinel + 폴백 버튼(그룹핑은 로드된 전체에 적용). */}
      <LoadMore
        hasNextPage={hasNextPage}
        isFetchingNextPage={isFetchingNextPage}
        onLoadMore={() => fetchNextPage()}
        itemCount={list.length}
      />
    </div>
  );
}
