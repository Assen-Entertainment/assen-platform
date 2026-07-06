import type { Meta, StoryObj } from "@storybook/nextjs";
import { DisclaimerNotice } from "@/components/ui/disclaimer-notice";

const meta = {
  title: "Notices/DisclaimerNotice",
  component: DisclaimerNotice,
  parameters: { layout: "padded" },
  argTypes: {
    title: { control: "text" },
    children: { control: "text" },
  },
  args: {
    title: "안내",
    children: "표시된 수수료·정산 금액은 확정 전 예시이며 실제와 다를 수 있습니다.",
  },
  render: (args) => (
    <div className="w-96 max-w-full">
      <DisclaimerNotice {...args} />
    </div>
  ),
} satisfies Meta<typeof DisclaimerNotice>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};

export const NoTitle: Story = {
  name: "제목 없음",
  args: { title: undefined, children: "본 화면의 가격·약관은 검토 전 placeholder 입니다." },
};
