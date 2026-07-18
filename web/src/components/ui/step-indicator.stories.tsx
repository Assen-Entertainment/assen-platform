import type { Meta, StoryObj } from "@storybook/nextjs";
import { StepIndicator } from "@/components/ui/step-indicator";

const STEPS = ["정보", "인증", "완료"];

const meta = {
  title: "Navigation/StepIndicator",
  component: StepIndicator,
  parameters: { layout: "centered" },
  argTypes: {
    current: { control: { type: "range", min: 0, max: 2, step: 1 } },
  },
  args: { steps: STEPS, current: 1 },
} satisfies Meta<typeof StepIndicator>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Playground: Story = {};

export const AllStages: Story = {
  name: "단계별",
  render: () => (
    <div className="flex flex-col gap-4">
      <StepIndicator steps={STEPS} current={0} />
      <StepIndicator steps={STEPS} current={1} />
      <StepIndicator steps={STEPS} current={2} />
    </div>
  ),
};
