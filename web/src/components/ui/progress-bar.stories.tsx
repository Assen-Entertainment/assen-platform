import type { Meta, StoryObj } from "@storybook/nextjs";
import { ProgressBar } from "@/components/ui/progress-bar";
import { creatorAccentVars } from "@/lib/creator-accent";

const meta = {
  title: "Feedback/ProgressBar",
  component: ProgressBar,
  parameters: { layout: "padded" },
  argTypes: {
    value: { control: { type: "range", min: 0, max: 100 } },
    max: { control: "number" },
    label: { control: "text" },
    showValue: { control: "boolean" },
    accent: { control: "boolean" },
  },
  args: { value: 60, max: 100, label: "업로드 진행", showValue: true },
  render: (args) => (
    <div className="w-80 max-w-full">
      <ProgressBar {...args} />
    </div>
  ),
} satisfies Meta<typeof ProgressBar>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};

export const BarOnly: Story = {
  name: "라벨 없음",
  args: { label: undefined, showValue: false, value: 40 },
};

export const CreatorAccent: Story = {
  name: "크리에이터 액센트",
  render: () => (
    <div className="w-80 max-w-full" style={creatorAccentVars("#E14B8A")}>
      <ProgressBar accent showValue label="목표 달성률" value={72} max={100} />
    </div>
  ),
};
