import Link from "next/link";
import { Avatar, ListItem, Divider, Button } from "@/components/ui";

const MENU = [
  { label: "알림 설정", subtitle: "푸시·이메일", href: "/notifications" },
  { label: "결제 수단", href: "/checkout" },
  { label: "주문 내역", href: "/orders" },
  { label: "멤버십 관리", href: "/membership" },
  { label: "계정 설정", href: "/settings" },
];

export default function MyPage() {
  return (
    <div className="mx-auto flex max-w-2xl flex-col gap-6">
      <section className="flex items-center gap-4">
        <Avatar fallback="나" size="xl" />
        <div className="flex min-w-0 flex-col gap-1">
          <span className="text-title-l text-on-surface">내 이름</span>
          <span className="text-body-s text-on-surface-variant">@me · 팔로잉 24 · 구독 2</span>
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
