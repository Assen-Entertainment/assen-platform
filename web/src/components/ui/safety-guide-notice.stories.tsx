import type { Meta, StoryObj } from "@storybook/nextjs";
import { SafetyGuideNotice } from "@/components/ui/safety-guide-notice";

const meta = {
  title: "Notices/SafetyGuideNotice",
  component: SafetyGuideNotice,
  parameters: { layout: "padded" },
  argTypes: {
    title: { control: "text" },
    children: { control: "text" },
  },
  args: {
    title: "안전 거래 안내",
    children: "결제는 안전결제(에스크로)로 보호되며, 문제가 있으면 신고 센터로 접수할 수 있어요.",
  },
  render: (args) => (
    <div className="w-96 max-w-full">
      <SafetyGuideNotice {...args} />
    </div>
  ),
} satisfies Meta<typeof SafetyGuideNotice>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};
