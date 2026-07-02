"use client";
import * as React from "react";
import {
  Button, TextField, Avatar, Chip, Badge, Tag, Switch, Checkbox, RadioGroup, RadioGroupItem,
  Spinner, Skeleton, Divider, PriceLabel, MonetizableItem, CreatorThumbCard, MembershipTierCard,
  EmptyState, SearchField, PostCard, ListItem, SegmentedControl, QuantityStepper,
  Dialog, DialogTrigger, DialogClose, DialogContent, DialogTitle, DialogDescription,
  Tabs, TabsList, TabsTrigger, TabsContent, TooltipProvider, Tooltip, TooltipTrigger, TooltipContent,
  DropdownMenu, DropdownMenuTrigger, DropdownMenuContent, DropdownMenuItem,
  OTPInput, StepIndicator, ConsentGroup, Breadcrumb, Pagination, RightRail,
} from "@/components/ui";
import { creatorAccentVars } from "@/lib/creator-accent";

/** DS 갤러리 — WSL `pnpm dev` → /gallery 에서 스크린샷↔Figma 시각비교용. 라이트/다크/액센트 포함. */
function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="flex flex-col gap-4">
      <h2 className="text-headline text-on-surface">{title}</h2>
      <div className="flex flex-wrap items-start gap-4">{children}</div>
    </section>
  );
}

export default function Gallery() {
  const [dark, setDark] = React.useState(false);
  const [seg, setSeg] = React.useState("all");
  const [qty, setQty] = React.useState(1);
  const [tab, setTab] = React.useState("posts");
  const [otp, setOtp] = React.useState("");
  const [consent, setConsent] = React.useState<string[]>([]);
  const [pageN, setPageN] = React.useState(1);
  return (
    <div className={dark ? "dark" : ""}>
      <TooltipProvider>
        <main className="min-h-screen bg-surface p-8 text-on-surface">
          <div className="mx-auto flex max-w-5xl flex-col gap-10">
            <header className="flex items-center justify-between">
              <h1 className="text-display-m">Assen DS 갤러리</h1>
              <Button variant="outline" onClick={() => setDark((d) => !d)}>{dark ? "라이트" : "다크"} 토글</Button>
            </header>

            <Section title="Buttons">
              <Button>Primary</Button>
              <Button variant="secondary">Secondary</Button>
              <Button variant="outline">Outline</Button>
              <Button variant="ghost">Ghost</Button>
              <Button disabled>Disabled</Button>
            </Section>

            <Section title="Form">
              <TextField label="이메일" placeholder="you@assen.kr" className="w-60" />
              <TextField label="에러" error errorText="필수 항목입니다" placeholder="..." className="w-60" />
              <SearchField className="w-60" />
              <div className="flex items-center gap-4">
                <Switch defaultChecked />
                <Checkbox defaultChecked />
                <RadioGroup defaultValue="a">
                  <div className="flex gap-3"><RadioGroupItem value="a" /><RadioGroupItem value="b" /></div>
                </RadioGroup>
                <QuantityStepper value={qty} onChange={setQty} />
              </div>
            </Section>

            <Section title="Data display">
              <Badge>중립</Badge><Badge variant="primary">인기</Badge><Badge variant="success">완료</Badge>
              <Badge variant="warning">대기</Badge><Badge variant="error">취소</Badge>
              <Tag>한정</Tag><Chip selected>전체</Chip><Chip>굿즈</Chip>
              <Avatar fallback="A" verified /><Avatar fallback="B" size="lg" />
              <PriceLabel amount={30000} /><PriceLabel amount={9900} suffix="/월" />
              <PriceLabel amount={5000} originalAmount={10000} discountPercent={50} />
              <Spinner /><Skeleton className="h-10 w-40" />
              <SegmentedControl options={[{ label: "전체", value: "all" }, { label: "포스트", value: "post" }]} value={seg} onValueChange={setSeg} />
              <Divider className="w-full" />
            </Section>

            <Section title="Commerce — MonetizableItem">
              <div className="grid w-full grid-cols-2 gap-4 sm:grid-cols-4">
                <MonetizableItem type="goods" title="굿즈 상품명" price="₩30,000" meta="재고 12개 · 한정" />
                <MonetizableItem type="digital" title="디지털 화보집" price="₩5,000" meta="다운로드 콘텐츠" />
                <MonetizableItem type="experience" title="포토카드 팬사인" price="₩12,000" meta="11/30 · 선착순 30" />
                <MonetizableItem type="coupon" title="10% 할인 쿠폰" price="₩3,000" meta="30일 유효" />
              </div>
            </Section>

            <Section title="Creator & Membership">
              <div className="grid w-full grid-cols-2 gap-4 sm:grid-cols-3">
                <CreatorThumbCard name="크리에이터 이름" meta="일러스트 · 팔로워 1.2k" />
                <MembershipTierCard name="베이직 멤버십" price={9900} benefits={["전용 콘텐츠 무제한", "월간 라이브"]} />
                <MembershipTierCard name="프리미엄" price={19900} badge="인기" featured benefits={["베이직 혜택 전부", "팬사인 우선", "멤버 전용 굿즈"]} />
              </div>
            </Section>

            <Section title="Feed — PostCard">
              <div className="w-full max-w-xl overflow-hidden rounded-lg border border-outline">
                <PostCard
                  creatorName="크리에이터 이름"
                  creatorMeta="@creator_handle · 3시간 전"
                  avatarFallback="C"
                  verified
                  body={"새 포스트를 올렸어요.\n팬 여러분 응원 감사합니다!"}
                  media={<div className="aspect-video w-full bg-surface-container-high" />}
                  likeCount={128}
                  commentCount={12}
                  liked
                />
              </div>
            </Section>

            <Section title="Overlays">
              <Dialog>
                <DialogTrigger asChild><Button>다이얼로그</Button></DialogTrigger>
                <DialogContent>
                  <DialogTitle>구독을 해지할까요?</DialogTitle>
                  <DialogDescription>다음 결제일부터 혜택이 중단됩니다.</DialogDescription>
                  <div className="flex justify-end gap-2">
                    <DialogClose asChild><Button variant="outline">취소</Button></DialogClose>
                    <Button>해지</Button>
                  </div>
                </DialogContent>
              </Dialog>
              <Tooltip><TooltipTrigger asChild><Button variant="outline">툴팁</Button></TooltipTrigger><TooltipContent>도움말 텍스트</TooltipContent></Tooltip>
              <DropdownMenu>
                <DropdownMenuTrigger asChild><Button variant="outline">메뉴</Button></DropdownMenuTrigger>
                <DropdownMenuContent>
                  <DropdownMenuItem>수정</DropdownMenuItem>
                  <DropdownMenuItem>공유</DropdownMenuItem>
                  <DropdownMenuItem destructive>삭제</DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            </Section>

            <Section title="Tabs / List">
              <div className="flex w-full max-w-md flex-col gap-4">
                <Tabs value={tab} onValueChange={setTab}>
                  <TabsList><TabsTrigger value="posts">포스트</TabsTrigger><TabsTrigger value="store">스토어</TabsTrigger><TabsTrigger value="membership">멤버십</TabsTrigger></TabsList>
                  <TabsContent value="posts" className="p-4 text-body-m">포스트 탭 내용</TabsContent>
                  <TabsContent value="store" className="p-4 text-body-m">스토어 탭 내용</TabsContent>
                  <TabsContent value="membership" className="p-4 text-body-m">멤버십 탭 내용</TabsContent>
                </Tabs>
                <div className="overflow-hidden rounded-lg border border-outline">
                  <ListItem title="알림 설정" subtitle="푸시·이메일" showChevron />
                  <Divider />
                  <ListItem title="다크 모드" trailing={<Switch />} />
                </div>
              </div>
            </Section>

            <Section title="Empty / Creator Accent">
              <EmptyState title="아직 콘텐츠가 없어요" description="첫 포스트를 올려 팬들과 소통을 시작해보세요." action={<Button size="sm">새로 만들기</Button>} />
              <div style={creatorAccentVars("#E14B8A")} className="rounded-lg bg-creator-accent p-4 text-on-creator-accent">
                크리에이터 액센트 스코프 (Coral · 자동 대비)
              </div>
            </Section>

            <Section title="E2 — 신규 컴포넌트">
              <OTPInput value={otp} onChange={setOtp} />
              <StepIndicator steps={["정보", "인증", "완료"]} current={1} />
              <ConsentGroup
                className="w-72"
                items={[
                  { id: "tos", label: "이용약관 동의", required: true },
                  { id: "priv", label: "개인정보 처리방침", required: true },
                  { id: "mkt", label: "마케팅 수신(선택)" },
                ]}
                value={consent}
                onChange={setConsent}
              />
              <Breadcrumb items={[{ label: "홈", href: "/" }, { label: "스토어", href: "/store" }, { label: "굿즈" }]} />
              <Pagination page={pageN} total={10} onPage={setPageN} />
              <RightRail className="!flex h-28 rounded-lg border">추천 슬롯</RightRail>
            </Section>
          </div>
        </main>
      </TooltipProvider>
    </div>
  );
}
