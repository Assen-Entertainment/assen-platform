"use client";
import Link from "next/link";
import { Avatar, ListItem, Divider, Button } from "@/components/ui";
import { useSession } from "@/lib/session";

const MENU = [
  { label: "알림 설정", subtitle: "푸시·이메일", href: "/settings/notifications" },
  { label: "결제 수단", href: "/settings/payments" },
  { label: "주문 내역", href: "/orders" },
  { label: "구독 관리", subtitle: "멤버십 해지·변경", href: "/mypage/subscriptions" },
  { label: "멤버십 둘러보기", href: "/membership" },
  { label: "계정 설정", href: "/settings/account" },
];

/** raw UUID(핸들 미설정 시 id 폴백) 판별 — 이 경우 @핸들을 노출하지 않는다. */
const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

export default function MyPage() {
  const { user } = useSession();
  const name = user?.name ?? "게스트";
  const initial = name.slice(0, 1);
  // 핸들이 raw UUID(=id 폴백)면 @UUID 노출 대신 미표기 — 닉네임만 보여준다.
  const rawHandle = user?.handle ?? "";
  const showHandle = Boolean(rawHandle) && rawHandle !== user?.id && !UUID_RE.test(rawHandle);

  return (
    <div className="mx-auto flex max-w-2xl flex-col gap-6">
      <section className="flex items-center gap-4">
        <Avatar fallback={initial} size="xl" />
        <div className="flex min-w-0 flex-col gap-1">
          <span className="text-title-l text-on-surface">{name}</span>
          <span className="text-body-s text-on-surface-variant">
            {showHandle ? `@${rawHandle} · ` : ""}팔로잉 24 · 구독 2
          </span>
        </div>
        <Button variant="outline" className="ml-auto" asChild>
          <Link href="/settings">프로필 편집</Link>
        </Button>
      </section>

      <div className="overflow-hidden rounded-lg border border-outline">
        {MENU.map((m, i) => (
          <div key={m.label}>
            {i > 0 ? <Divider /> : null}
            <Link href={m.href} className="block transition-colors hover:bg-surface-container-high">
              <ListItem title={m.label} subtitle={m.subtitle} showChevron />
            </Link>
          </div>
        ))}
      </div>
    </div>
  );
}
