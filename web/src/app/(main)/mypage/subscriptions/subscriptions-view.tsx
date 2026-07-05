"use client";
import Link from "next/link";
import {
  Card,
  CardBody,
  Button,
  Divider,
  StatusChip,
  EmptyState,
  Sheet,
  SheetTrigger,
  SheetContent,
  SheetTitle,
  SheetDescription,
  SheetClose,
} from "@/components/ui";
import { useToast } from "@/components/ui/use-toast";
import { useSubscriptions, useCancelSubscription } from "@/lib/api/queries";
import { won } from "@/lib/checkout";
import { ApiError, apiErrorMessage, type Subscription } from "@/lib/api";

export function SubscriptionsView({ subscriptions }: { subscriptions: Subscription[] }) {
  const { toast } = useToast();
  // USE_API면 실 목록/해지, 아니면 mock — 해지 시 낙관적 cancelScheduled=true("해지 예정").
  const { data } = useSubscriptions(subscriptions);
  const subs = data ?? subscriptions;
  const cancelMut = useCancelSubscription();
  const isCancelled = (sub: Subscription) => Boolean(sub.cancelScheduled) || sub.status === "cancelled";

  const cancel = (sub: Subscription) => {
    cancelMut.mutate(sub.id, {
      onSuccess: () =>
        toast({
          title: "구독을 해지했어요",
          description: `${sub.creatorName} · ${sub.tierName} — 다음 결제일부터 중단됩니다.`,
        }),
      onError: (e) => {
        // 401은 전역 세션 가드가 처리 → 그 외는 error code로 안내(SubscriptionNotCancellable 등, detail 폴백).
        if (e instanceof ApiError && e.status === 401) return;
        toast({ title: "구독 해지를 처리하지 못했어요", description: apiErrorMessage(e) });
      },
    });
  };

  return (
    <div className="mx-auto flex max-w-2xl flex-col gap-4">
      <h1 className="text-headline text-on-surface">구독 관리</h1>
      {subs.length ? (
        <div className="flex flex-col gap-3">
          {subs.map((sub) => {
            const done = isCancelled(sub);
            return (
              <Card key={sub.id}>
                <CardBody className="flex flex-col gap-3">
                  <div className="flex items-center justify-between gap-3">
                    <div className="flex min-w-0 flex-col">
                      <Link
                        href={`/creator/${sub.creatorHandle}`}
                        className="line-clamp-1 text-body-l text-on-surface hover:underline"
                      >
                        {sub.creatorName}
                      </Link>
                      <span className="text-caption text-on-surface-variant">{sub.tierName} 멤버십</span>
                    </div>
                    <StatusChip variant={done ? "neutral" : "success"}>{done ? "해지 예정" : "구독 중"}</StatusChip>
                  </div>
                  <Divider />
                  <div className="flex items-center justify-between text-body-s">
                    <span className="text-on-surface-variant">{done ? "종료 예정일" : "다음 결제일"}</span>
                    <span className="tabular-nums text-on-surface">{sub.nextBillingDate}</span>
                  </div>
                  <div className="flex items-center justify-between text-body-s">
                    <span className="text-on-surface-variant">결제 금액</span>
                    <span className="tabular-nums text-on-surface">
                      {won(sub.price)} / {sub.period}
                    </span>
                  </div>
                  {!done ? (
                    <Sheet>
                      <SheetTrigger asChild>
                        <Button variant="outline" size="sm" className="self-start">
                          구독 해지
                        </Button>
                      </SheetTrigger>
                      <SheetContent side="bottom">
                        <SheetTitle>구독을 해지할까요?</SheetTitle>
                        <SheetDescription>
                          {sub.creatorName}의 {sub.tierName} 멤버십을 해지합니다. 다음 결제일({sub.nextBillingDate})부터
                          결제가 중단되며, 남은 기간 동안은 혜택을 계속 이용할 수 있어요.
                        </SheetDescription>
                        <div className="mt-2 flex flex-col gap-2">
                          <SheetClose asChild>
                            <Button
                              variant="primary"
                              className="w-full bg-error text-on-error hover:opacity-90"
                              onClick={() => cancel(sub)}
                            >
                              해지하기
                            </Button>
                          </SheetClose>
                          <SheetClose asChild>
                            <Button variant="ghost" className="w-full">
                              유지하기
                            </Button>
                          </SheetClose>
                        </div>
                      </SheetContent>
                    </Sheet>
                  ) : null}
                </CardBody>
              </Card>
            );
          })}
        </div>
      ) : (
        <EmptyState
          title="구독 중인 멤버십이 없어요"
          description="크리에이터를 후원하고 전용 혜택을 받아보세요."
          action={
            <Button asChild>
              <Link href="/membership">멤버십 둘러보기</Link>
            </Button>
          }
        />
      )}
    </div>
  );
}
