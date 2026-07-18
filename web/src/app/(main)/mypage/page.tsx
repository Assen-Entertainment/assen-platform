"use client";
import Link from "next/link";
import { Avatar, ListItem, Divider, Button, IdentityVerifyBanner } from "@/components/ui";
import { useSession } from "@/lib/session";
import { useSubscriptions } from "@/lib/api/queries";

/** 마이 = 내 활동 허브(주문·구독·멤버십). 알림/결제/계정 등 환경설정은 /settings 단일 소유 —
 *  기존엔 마이가 /settings/* 3개를 그대로 재노출해 두 허브가 같은 목적지로 중복됐다(blindspot #3). */
const MENU = [
  { label: "주문 내역", href: "/orders" },
  { label: "구독 관리", subtitle: "멤버십 해지·변경", href: "/mypage/subscriptions" },
  { label: "멤버십 둘러보기", href: "/membership" },
  { label: "설정", subtitle: "알림·결제·계정·차단", href: "/settings" },
];

/** raw UUID(핸들 미설정 시 id 폴백) 판별 — 이 경우 @핸들을 노출하지 않는다. */
const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

export default function MyPage() {
  const { user } = useSession();
  const name = user?.name ?? "게스트";
  const initial = name.slice(0, 1);
  // 크리에이터면 스튜디오로, 아니면 셀프 개설로 안내(팬/크리에이터 모드 진입점).
  const isCreator = user?.isCreator ?? false;
  const creatorEntry = isCreator
    ? { label: "크리에이터 스튜디오", subtitle: "내 페이지·상품 관리", href: "/studio" }
    : { label: "크리에이터 되기", subtitle: "내 크리에이터 페이지 개설", href: "/become-creator" };
  const menu = [creatorEntry, ...MENU];
  // 핸들이 raw UUID(=id 폴백)면 @UUID 노출 대신 미표기 — 닉네임만 보여준다.
  const rawHandle = user?.handle ?? "";
  const showHandle = Boolean(rawHandle) && rawHandle !== user?.id && !UUID_RE.test(rawHandle);
  // 실 구독 수(하드코딩 "구독 2" 제거) — 취소분 제외. 팔로잉 수는 아직 집계 소스가 없어 표기하지 않는다.
  const { data: subs } = useSubscriptions();
  const subCount = (subs ?? []).filter((s) => s.status !== "cancelled").length;

  return (
    <div className="mx-auto flex max-w-2xl flex-col gap-6">
      {/* 미인증 팬 프로액티브 안내 — 게이트 상호작용(팔로우·구독·구매) 전에 본인인증을 유도. */}
      {user && user.kycStatus !== "verified" ? (
        <IdentityVerifyBanner
          verified={false}
          action={
            <Button size="sm" asChild>
              <Link href="/verify?next=/mypage">본인인증하기</Link>
            </Button>
          }
        />
      ) : null}
      <section className="flex items-center gap-4">
        <Avatar fallback={initial} size="xl" />
        <div className="flex min-w-0 flex-col gap-1">
          <span className="text-title-l text-on-surface">{name}</span>
          <span className="text-body-s text-on-surface-variant">
            {showHandle ? `@${rawHandle} · ` : ""}구독 {subCount}
          </span>
        </div>
        <Button variant="outline" className="ml-auto" asChild>
          <Link href="/settings/account">프로필 편집</Link>
        </Button>
      </section>

      <div className="overflow-hidden rounded-lg border border-outline">
        {menu.map((m, i) => (
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
