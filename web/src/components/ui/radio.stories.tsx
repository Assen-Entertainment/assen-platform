import type { Meta, StoryObj } from "@storybook/nextjs";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio";

const meta = {
  title: "Forms/Radio",
  component: RadioGroup,
  parameters: { layout: "centered" },
} satisfies Meta<typeof RadioGroup>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {
  render: () => (
    <RadioGroup defaultValue="monthly">
      {[
        { value: "monthly", label: "월간 결제" },
        { value: "yearly", label: "연간 결제 (2개월 무료)" },
        { value: "onetime", label: "1회 후원" },
      ].map((o) => (
        <label key={o.value} className="flex items-center gap-2 text-body-m text-on-surface">
          <RadioGroupItem value={o.value} /> {o.label}
        </label>
      ))}
    </RadioGroup>
  ),
};
