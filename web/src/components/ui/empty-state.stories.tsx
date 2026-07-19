import type { Meta, StoryObj } from "@storybook/nextjs";
import { EmptyState } from "@/components/ui/empty-state";
import { Button } from "@/components/ui/button";
import { ReceiptLineIcon, MembershipLineIcon } from "@/components/ui/empty-state-icons";

const meta = {
  title: "Feedback/EmptyState",
  component: EmptyState,
  parameters: { layout: "centered" },
  argTypes: {
    title: { control: "text" },
    description: { control: "text" },
  },
  args: {
    title: "주문 내역이 없어요",
    description: "마음에 드는 아이템을 둘러보세요.",
  },
} satisfies Meta<typeof EmptyState>;

export default meta;
type Story = StoryObj<typeof meta>;

/** 기본 — 컨텍스트 라인 아이콘 + CTA. 원판=중립 surface 톤, 아이콘=라인 24px. */
export const Default: Story = {
  render: (args) => (
    <EmptyState {...args} icon={<ReceiptLineIcon />} action={<Button size="sm">스토어 가기</Button>} />
  ),
};

/** 아이콘 미전달 — 폴백 라인 아이콘(InboxLineIcon)으로 민 원판("깨진 이미지")을 방지. */
export const FallbackIcon: Story = {
  render: (args) => <EmptyState {...args} title="알림이 없어요" description="새 소식이 오면 여기에 표시됩니다." />,
};

/** 설명 없는 컴팩트 변형. */
export const TitleOnly: Story = {
  render: () => <EmptyState icon={<MembershipLineIcon />} title="구독 중인 멤버십이 없어요" />,
};
