"use client";
import * as React from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
  Button,
  Tabs, TabsList, TabsTrigger, TabsContent,
  PostCard, MonetizableItem, MembershipTierCard, ErrorState, EmptyState,
  CreatorHomeHeader, GiftSheet, LockedOverlay, DisclaimerNotice, MediaImage, ReportSheet,
  DropdownMenu, DropdownMenuTrigger, DropdownMenuContent, DropdownMenuItem,
  Dialog, DialogContent, DialogClose, DialogTitle, DialogDescription,
} from "@/components/ui";
import { useToast } from "@/components/ui/use-toast";
import { MoreIcon } from "@/lib/icons";
import { creatorAccentVars } from "@/lib/creator-accent";
import { gradientStyle } from "@/lib/placeholder";
import { useCreator, useToggleFollow, usePosts, useToggleLike, useBlockCreator, useUnblockCreator, useSubscriptions, useChangeSubscriptionTier, useShippingCheckoutAvailable, useReport } from "@/lib/api/queries";
import { ApiError, apiErrorMessage, type Creator, type Page, type Post, type Product, type MembershipTier } from "@/lib/api";
import { won } from "@/lib/checkout";
import { useSession } from "@/lib/session";
import { savePendingAction, readPendingAction, clearPendingAction } from "@/lib/auth-return";

/** CreatorProfile 뷰 — 동적 + React Query. 팔로우=낙관적 뮤테이션(캐시 즉시 반영). */
export function CreatorProfileView({
  creator,
  posts,
  products,
  tiers,
}: {
  creator: Creator;
  posts: Page<Post>;
  products: Product[];
  tiers: MembershipTier[];
}) {
  const router = useRouter();
  const pathname = usePathname();
  const { user, mounted } = useSession();
  const { toast } = useToast();
  const [tab, setTab] = React.useState("posts");
  const [giftOpen, setGiftOpen] = React.useState(false);
  const { data, isError, refetch } = useCreator(creator.handle, creator);
  const c = data ?? creator;
  const follow = useToggleFollow(creator.handle);
  // 스토어 탭도 /store와 동일한 배송(굿즈) 결제 게이트를 따른다(상태 일관성).
  const shippingAvailable = useShippingCheckoutAvailable();
  const accent = c.accentColor;
  const initial = c.name.slice(0, 1);
  // 본인 프로필 여부 — 세션 유저의 크리에이터 핸들이 이 프로필 핸들과 같으면 주인.
  // 주인이면 팔로우·후원 컨트롤을 숨긴다(자기 팔로우/후원 방지).
  const isOwner = Boolean(user?.handle && user.handle === c.handle);

  // 팔로우 클릭 — 비로그인이면 미완료 액션을 저장하고 로그인으로(성공 시 복귀+자동 재실행).
  const from = pathname || `/creator/${creator.handle}`;
  const onToggleFollow = () => {
    if (mounted && !user) {
      savePendingAction({ action: "follow", handle: creator.handle, from });
      router.push(`/login?next=${encodeURIComponent(from)}`);
      return;
    }
    follow.mutate(!c.following, {
      // 실패 시 캐시는 useToggleFollow가 롤백하지만 사용자에겐 아무 안내가 없었음 → 토스트로 명시.
      // 401은 전역 세션 가드가 처리 → 그 외만 안내(차단/해제 토스트 패턴과 동일).
      onError: (e) => {
        if (e instanceof ApiError && e.status === 401) return;
        toast({ title: "팔로우하지 못했어요", description: apiErrorMessage(e) });
      },
    });
  };

  // 로그인 복귀 후 미완료 팔로우 자동 재실행(팔로우만 — 좋아요·구독은 후속).
  //  clear 후 readPendingAction()은 null이라 후속 렌더의 재실행은 no-op(멱등).
  React.useEffect(() => {
    if (!mounted || !user) return;
    const pending = readPendingAction();
    if (pending?.action !== "follow" || pending.handle !== creator.handle) return;
    clearPendingAction();
    if (!c.following) {
      follow.mutate(true, {
        onSuccess: () => toast({ title: `${c.name}님을 팔로우했어요` }),
      });
    }
  }, [mounted, user, creator.handle, c.following, c.name, follow, toast]);

  // 포스트 좋아요 — 공용 useToggleLike(캐시 통일). 프로필 포스트도 ["posts", creatorId]
  // 캐시로 하이드레이트 → 뮤테이션이 즉시 UI에 반영되고 피드·상세와 동일 경로.
  const { data: postData } = usePosts(creator.id, posts);
  const postList = postData ?? posts.items;
  const toggleLike = useToggleLike();

  // 팬 개인 차단(R4-W3) — 차단은 파괴적 UX(자동 언팔) → 확인 다이얼로그. 해제는 비파괴적 → 즉시.
  const block = useBlockCreator();
  const unblock = useUnblockCreator();
  const [confirmBlockOpen, setConfirmBlockOpen] = React.useState(false);

  // 신고(안전) — 피드 더보기와 동일 배선(ReportSheet + useReport → POST /safety/fan-reports).
  // 서술(narrative)은 서버로만 전달되고 analytics엔 담기지 않는다(useReport가 유형 코드만 계측).
  const report = useReport();
  const [reportOpen, setReportOpen] = React.useState(false);

  // 멤버십 탭 — 이 크리에이터에 내 활성 구독이 있으면 "구독 중" 배지+티어 전환(업/다운그레이드) 제공.
  const { data: subsData } = useSubscriptions();
  const mySub = (subsData ?? []).find((s) => s.creatorHandle === c.handle && s.status !== "cancelled");
  const changeTier = useChangeSubscriptionTier();
  const [pendingTier, setPendingTier] = React.useState<MembershipTier | null>(null);

  const onConfirmTierChange = () => {
    if (!mySub || !pendingTier) return;
    const targetTier = pendingTier;
    changeTier.mutate(
      { id: mySub.id, tierId: targetTier.id },
      {
        onSuccess: () =>
          toast({ title: "멤버십 티어를 변경했어요", description: `${targetTier.name} 멤버십으로 변경됐어요.` }),
        onError: (e) => {
          // 401은 전역 세션 가드가 처리 → 그 외는 error code로 안내(SubscriptionNotActive·TierNotFound 등).
          if (e instanceof ApiError && e.status === 401) return;
          toast({ title: "티어를 변경하지 못했어요", description: apiErrorMessage(e) });
        },
      },
    );
    setPendingTier(null);
  };

  const share = async (id: string) => {
    const url = `${window.location.origin}/post/${id}`;
    try {
      await navigator.clipboard.writeText(url);
      toast({ title: "링크를 복사했어요", description: url });
    } catch {
      toast({ title: "링크 복사에 실패했어요" });
    }
  };

  const onConfirmBlock = () => {
    block.mutate(
      { creatorId: c.id, handle: c.handle },
      {
        onSuccess: () =>
          toast({ title: "차단했어요", description: `${c.name}님의 콘텐츠가 더 이상 보이지 않아요.` }),
        onError: (e) => {
          // 401은 전역 세션 가드가 처리 → 그 외만 안내.
          if (e instanceof ApiError && e.status === 401) return;
          toast({ title: "차단하지 못했어요", description: apiErrorMessage(e) });
        },
      },
    );
    setConfirmBlockOpen(false);
  };

  const onUnblock = () => {
    unblock.mutate(
      { creatorId: c.id, handle: c.handle },
      {
        onSuccess: () =>
          toast({ title: "차단을 해제했어요", description: `${c.name}님의 콘텐츠를 다시 볼 수 있어요.` }),
        onError: (e) => {
          if (e instanceof ApiError && e.status === 401) return;
          toast({ title: "해제하지 못했어요", description: apiErrorMessage(e) });
        },
      },
    );
  };

  if (isError && !data) {
    return (
      <div className="flex min-h-[50vh] items-center justify-center">
        <ErrorState onRetry={() => refetch()} />
      </div>
    );
  }

  return (
    <div
      style={accent ? creatorAccentVars(accent) : undefined}
      className="mx-auto flex max-w-4xl flex-col gap-2 [animation:fade-up_500ms_ease-out]"
    >
      <CreatorHomeHeader
        name={c.name}
        handle={c.handle}
        initial={initial}
        avatarUrl={c.avatarUrl}
        coverUrl={c.coverUrl}
        followers={c.followers}
        posts={c.posts}
        verified={c.verified}
        bio={c.bio}
        accent={Boolean(accent)}
        following={c.following}
        followPending={follow.isPending}
        onToggleFollow={onToggleFollow}
        onGift={() => setGiftOpen(true)}
        isOwner={isOwner}
        followersHref={`/creator/${c.handle}/followers`}
        menu={
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="outline" size="icon" aria-label="더보기">
                <MoreIcon aria-hidden className="size-5" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              {c.blocked ? (
                <DropdownMenuItem onSelect={onUnblock} disabled={unblock.isPending}>
                  차단 해제
                </DropdownMenuItem>
              ) : (
                <DropdownMenuItem destructive onSelect={() => setConfirmBlockOpen(true)}>
                  차단하기
                </DropdownMenuItem>
              )}
              {!isOwner ? (
                <DropdownMenuItem destructive onSelect={() => setReportOpen(true)}>
                  신고하기
                </DropdownMenuItem>
              ) : null}
            </DropdownMenuContent>
          </DropdownMenu>
        }
      />

      {c.blocked ? (
        // 차단됨 — 배너 + 콘텐츠 숨김(포스트/스토어/멤버십 자리에 안내 + 해제 버튼).
        <div className="flex flex-col gap-4 px-2 pt-2">
          <DisclaimerNotice title="차단한 크리에이터예요">
            이 크리에이터의 포스트·스토어·멤버십을 숨기고 있어요. 차단을 해제하면 다시 볼 수 있어요.
          </DisclaimerNotice>
          <EmptyState
            icon={<span className="text-2xl">🚫</span>}
            title="콘텐츠를 숨기고 있어요"
            description="차단을 해제하면 이 크리에이터의 포스트와 상품을 다시 볼 수 있어요."
            action={
              <Button variant="outline" onClick={onUnblock} disabled={unblock.isPending}>
                차단 해제
              </Button>
            }
          />
        </div>
      ) : (
      <Tabs value={tab} onValueChange={setTab} className="px-2">
        <TabsList>
          <TabsTrigger value="posts">포스트</TabsTrigger>
          <TabsTrigger value="store">스토어</TabsTrigger>
          <TabsTrigger value="membership">멤버십</TabsTrigger>
        </TabsList>

        <TabsContent value="posts" className="pt-2">
          {postList.length === 0 ? (
            <EmptyState
              title="아직 포스트가 없어요"
              description="이 크리에이터는 아직 포스트를 올리지 않았어요. 스토어·멤버십을 먼저 둘러보세요."
            />
          ) : (
          <div className="overflow-hidden rounded-lg border border-outline bg-surface shadow-1">
            {postList.map((p) => (
              <PostCard
                key={p.id}
                creatorName={p.creatorName}
                creatorMeta={p.creatorMeta}
                verified={p.verified}
                avatarFallback={initial}
                avatarTone={c.handle}
                body={p.body}
                media={
                  p.locked ? (
                    // 잠긴 콘텐츠(루브릭 #16) — 실 미디어(있으면) 위 블러 + 락 + 해제 CTA(→ 멤버십 탭).
                    <MediaImage
                      src={p.mediaUrl}
                      alt={`${p.creatorName}의 포스트 미디어`}
                      gradientStyle={gradientStyle(p.id)}
                      className="aspect-video w-full"
                    >
                      <LockedOverlay
                        description="멤버십에 가입하면 이 포스트를 볼 수 있어요."
                        cta={
                          <Button size="sm" variant="accent" onClick={() => setTab("membership")}>
                            멤버십 보기
                          </Button>
                        }
                      />
                    </MediaImage>
                  ) : (
                    <Link href={`/post/${p.id}`} aria-label="포스트 상세 보기" className="block">
                      <MediaImage
                        src={p.mediaUrl}
                        alt={`${p.creatorName}의 포스트 미디어`}
                        gradientStyle={gradientStyle(p.id)}
                        className="aspect-video w-full transition-opacity hover:opacity-90"
                      />
                    </Link>
                  )
                }
                likeCount={p.likeCount}
                commentCount={p.commentCount}
                liked={p.liked}
                onLike={() => toggleLike.mutate({ id: p.id, next: !p.liked })}
                onComment={() => router.push(`/post/${p.id}`)}
                onShare={() => share(p.id)}
              />
            ))}
          </div>
          )}
        </TabsContent>

        <TabsContent value="store" className="pt-4">
          {products.length === 0 ? (
            <EmptyState
              title="아직 상품이 없어요"
              description="이 크리에이터는 아직 상품을 등록하지 않았어요. 포스트·멤버십을 먼저 둘러보세요."
            />
          ) : (
            <div className="grid grid-cols-2 gap-4 sm:grid-cols-3">
              {products.map((p) => {
                // /store와 동일한 상태 규칙 — 품절 우선(비활성 "품절"), 굿즈 배송 게이트("준비 중").
                const soldOut = Boolean(p.soldOut) || p.stock === 0;
                const goodsGated = p.type === "goods" && !shippingAvailable;
                return (
                  <MonetizableItem
                    key={p.id}
                    type={p.type}
                    title={p.title}
                    price={`₩${p.price.toLocaleString("ko-KR")}`}
                    meta={soldOut ? "품절" : p.meta}
                    mediaUrl={p.mediaUrl}
                    actionDisabled={soldOut || goodsGated}
                    ctaLabel={soldOut ? "품절" : goodsGated ? "준비 중" : undefined}
                    onAction={() => router.push(`/store/${p.id}`)}
                  />
                );
              })}
            </div>
          )}
        </TabsContent>

        <TabsContent value="membership" className="pt-4">
          {tiers.length === 0 ? (
            <EmptyState
              title="아직 멤버십이 없어요"
              description="이 크리에이터는 아직 멤버십을 열지 않았어요. 포스트·스토어를 먼저 둘러보세요."
            />
          ) : (
            <div className="grid gap-4 sm:grid-cols-3">
              {tiers.map((t, i) => {
                // 내 활성 구독이 이 크리에이터에 있으면: 현재 티어는 "구독 중"(비활성), 그 외는 "이 티어로 변경".
                const isCurrent = mySub?.tierId === t.id;
                // 무료 멤버십(ASS-297) — 신규 가입 CTA를 "무료로 시작하기"로. 체크아웃이 무료 획득을 처리한다.
                const free = t.pricingKind === "free";
                return (
                  <MembershipTierCard
                    key={t.id}
                    name={t.name}
                    price={t.price}
                    period={t.period}
                    benefits={t.benefits}
                    badge={t.badge}
                    featured={t.featured}
                    accent={t.featured}
                    inheritNote={i > 0 ? `${tiers[i - 1]?.name ?? ""} 혜택 포함` : undefined}
                    currentPlan={isCurrent}
                    ctaLabel={mySub ? "이 티어로 변경" : free ? "무료로 시작하기" : "구독하기"}
                    onSubscribe={
                      mySub
                        ? () => setPendingTier(t)
                        : () =>
                            router.push(
                              `/checkout?tier=${encodeURIComponent(t.id)}&creator=${encodeURIComponent(c.handle)}`,
                            )
                    }
                  />
                );
              })}
            </div>
          )}
        </TabsContent>
      </Tabs>
      )}

      {/* 멤버십 티어 전환 확인 — 현재 → 새 티어, 가격 변화 안내. */}
      <Dialog open={pendingTier !== null} onOpenChange={(o) => !o && setPendingTier(null)}>
        <DialogContent>
          <DialogTitle>멤버십 티어를 변경할까요?</DialogTitle>
          <DialogDescription>
            {mySub && pendingTier ? (
              <>
                {mySub.tierName}({won(mySub.price)}/{mySub.period}) → {pendingTier.name}(
                {won(pendingTier.price)}/{pendingTier.period})로 변경돼요.
                {pendingTier.price > mySub.price
                  ? " 다음 결제부터 인상된 금액이 적용됩니다."
                  : pendingTier.price < mySub.price
                    ? " 다음 결제부터 인하된 금액이 적용됩니다."
                    : ""}
              </>
            ) : null}
          </DialogDescription>
          <div className="mt-1 flex gap-2">
            <DialogClose asChild>
              <Button variant="outline" className="flex-1">
                취소
              </Button>
            </DialogClose>
            <Button className="flex-1" onClick={onConfirmTierChange} disabled={changeTier.isPending}>
              변경하기
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      <GiftSheet open={giftOpen} onOpenChange={setGiftOpen} creatorName={c.name} />

      {/* 신고 시트 — 피드와 동일 배선. USE_API면 /safety/fan-reports 실 접수, 아니면 mock(sleep). */}
      <ReportSheet
        open={reportOpen}
        onOpenChange={setReportOpen}
        onSubmit={(payload) => {
          report.mutate(
            { reportType: payload.reason, narrative: payload.detail || undefined },
            {
              onSuccess: () =>
                toast({ title: "신고가 접수되었어요", description: "운영팀이 검토 후 조치할게요." }),
              onError: (e) => {
                // 401은 전역 세션 가드가 처리 → 그 외 오류만 안내.
                if (!(e instanceof ApiError && e.status === 401)) {
                  toast({ title: "신고를 접수하지 못했어요", description: "잠시 후 다시 시도해 주세요." });
                }
              },
            },
          );
          setReportOpen(false);
        }}
      />

      {/* 차단 확인 — 파괴적 UX(자동 언팔로우 안내). 기존 Dialog 패턴 재사용. */}
      <Dialog open={confirmBlockOpen} onOpenChange={setConfirmBlockOpen}>
        <DialogContent>
          <DialogTitle>{c.name}님을 차단할까요?</DialogTitle>
          <DialogDescription>
            차단하면 이 크리에이터의 포스트·활동이 보이지 않고, 팔로우가 자동으로 해제돼요. 차단은
            설정 &gt; 차단 목록에서 언제든 해제할 수 있어요.
          </DialogDescription>
          <div className="mt-1 flex gap-2">
            <DialogClose asChild>
              <Button variant="outline" className="flex-1">
                취소
              </Button>
            </DialogClose>
            <Button
              className="flex-1 bg-error text-on-error hover:opacity-90"
              onClick={onConfirmBlock}
              disabled={block.isPending}
            >
              차단하기
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
