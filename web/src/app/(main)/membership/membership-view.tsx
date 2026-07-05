"use client";
import Link from "next/link";
import { Card, CardBody, Button, Divider, Avatar, StatusChip, EmptyState } from "@/components/ui";
import { useSubscriptions } from "@/lib/api/queries";
import { useSession } from "@/lib/session";
import { won } from "@/lib/checkout";
import type { Subscription } from "@/lib/api";

/**
 * 멤버십 허브 — 내 활성 구독을 관리하고, 크리에이터 둘러보기로 새 멤버십 가입을 유도한다.
 * 구독 시작은 항상 크리에이터 프로필(멤버십 탭) 컨텍스트에서만 이뤄진다(전역 직접 구독 동선 제거).
 */
export function MembershipView({ subscriptions }: { subscriptions: Subscription[] }) {
  const { user, mounted } = useSession();
  // USE_API면 실 목록(비로그인=빈 목록), 아니면 mock. 해지 예정도 만료 전까지 활성이므로 함께 노출.
  const { data } = useSubscriptions(subscriptions);
  const subs = (data ?? subscriptions).filter((s) => s.status !== "cancelled");
  const loggedIn = mounted && Boolean(user);

  return (
    <div className="mx-auto flex max-w-2xl flex-col gap-6">
      <div className="flex flex-col gap-2">
        <h1 className="text-headline text-on-surface">내 멤버십</h1>
        <p className="text-body-m text-on-surface-variant">
          구독 중인 크리에이터를 관리하고, 새로운 크리에이터를 둘러보세요.
        </p>
      </div>

      {subs.length ? (
        <section className="flex flex-col gap-3" aria-label="내 멤버십 목록">
          {subs.map((sub) => {
            const scheduled = Boolean(sub.cancelScheduled);
            return (
              <Card key={sub.id}>
                <CardBody className="flex flex-col gap-3">
                  <div className="flex items-center gap-3">
                    <Avatar fallback={sub.creatorName.slice(0, 1)} tone={sub.creatorHandle} size="lg" />
                    <div className="flex min-w-0 flex-1 flex-col">
                      <Link
                        href={`/creator/${sub.creatorHandle}`}
                        className="line-clamp-1 text-body-l text-on-surface hover:underline"
                      >
                        {sub.creatorName}
                      </Link>
                      <span className="text-caption text-on-surface-variant">{sub.tierName} 멤버십</span>
                    </div>
                    <StatusChip variant={scheduled ? "neutral" : "success"}>
                      {scheduled ? "해지 예정" : "구독 중"}
                    </StatusChip>
                  </div>
                  <Divider />
                  <div className="flex items-center justify-between text-body-s">
                    <span className="text-on-surface-variant">{scheduled ? "종료 예정일" : "다음 결제일"}</span>
                    <span className="tabular-nums text-on-surface">{sub.nextBillingDate}</span>
                  </div>
                  <div className="flex items-center justify-between text-body-s">
                    <span className="text-on-surface-variant">결제 금액</span>
                    <span className="tabular-nums text-on-surface">
                      {won(sub.price)} / {sub.period}
                    </span>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    <Button variant="outline" size="sm" asChild>
                      <Link href="/mypage/subscriptions">구독 관리</Link>
                    </Button>
                    {/* 티어 변경은 크리에이터 프로필 멤버십 탭에서(대상 크리에이터 컨텍스트 유지). */}
                    <Button variant="ghost" size="sm" asChild>
                      <Link href={`/creator/${sub.creatorHandle}`}>티어 변경</Link>
                    </Button>
                  </div>
                </CardBody>
              </Card>
            );
          })}
          <Button variant="outline" asChild className="self-start">
            <Link href="/discovery">크리에이터 둘러보기</Link>
          </Button>
        </section>
      ) : (
        <EmptyState
          title={loggedIn ? "아직 구독 중인 멤버십이 없어요" : "멤버십으로 크리에이터를 후원해 보세요"}
          description="마음에 드는 크리에이터의 프로필에서 멤버십에 가입하면 전용 포스트·혜택을 받을 수 있어요."
          action={
            <Button asChild>
              <Link href="/discovery">크리에이터 둘러보기</Link>
            </Button>
          }
        />
      )}
    </div>
  );
}
