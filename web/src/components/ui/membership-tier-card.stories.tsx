import type { Meta, StoryObj } from "@storybook/nextjs";
import { MembershipTierCard } from "@/components/ui/membership-tier-card";

const meta = {
  title: "Commerce/MembershipTierCard",
  component: MembershipTierCard,
  parameters: { layout: "centered" },
  render: (args) => (
    <div className="w-72">
      <MembershipTierCard {...args} />
    </div>
  ),
  args: {
    name: "베이직 멤버십",
    price: 9900,
    benefits: ["전용 콘텐츠 무제한", "월간 라이브"],
  },
} satisfies Meta<typeof MembershipTierCard>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Basic: Story = {};

export const Featured: Story = {
  name: "추천 티어",
  args: {
    name: "프리미엄",
    price: 19900,
    badge: "인기",
    featured: true,
    benefits: ["베이직 혜택 전부", "팬사인 우선", "멤버 전용 굿즈"],
    inheritNote: "베이직 혜택 포함",
  },
};

export const CurrentPlan: Story = {
  name: "구독 중",
  args: {
    name: "베이직 멤버십",
    price: 9900,
    currentPlan: true,
    benefits: ["전용 콘텐츠 무제한", "월간 라이브"],
  },
};

export const Comparison: Story = {
  name: "티어 비교",
  render: () => (
    <div className="grid w-[36rem] grid-cols-2 gap-4">
      <MembershipTierCard name="베이직" price={9900} benefits={["전용 콘텐츠", "월간 라이브"]} />
      <MembershipTierCard
        name="프리미엄"
        price={19900}
        badge="인기"
        featured
        benefits={["베이직 혜택 전부", "팬사인 우선", "멤버 전용 굿즈"]}
        inheritNote="베이직 혜택 포함"
      />
    </div>
  ),
};
