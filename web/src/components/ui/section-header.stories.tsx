import type { Meta, StoryObj } from "@storybook/nextjs";
import { SectionHeader } from "@/components/ui/section-header";
import { TextLink } from "@/components/ui/text-link";

const meta = {
  title: "Layout/SectionHeader",
  component: SectionHeader,
  parameters: { layout: "padded" },
  argTypes: {
    title: { control: "text" },
    description: { control: "text" },
    as: { control: "inline-radio", options: ["h2", "h3"] },
  },
  args: { title: "인기 크리에이터", description: "이번 주 가장 많은 사랑을 받은 창작자" },
  render: (args) => (
    <div className="w-[32rem] max-w-full">
      <SectionHeader {...args} />
    </div>
  ),
} satisfies Meta<typeof SectionHeader>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};

export const WithAction: Story = {
  name: "더보기 액션",
  args: {
    title: "새로운 굿즈",
    description: "방금 올라온 한정 상품",
    action: <TextLink href="#">전체 보기</TextLink>,
  },
};

export const TitleOnly: Story = {
  name: "제목만",
  args: { title: "추천 포스트", description: undefined },
};
