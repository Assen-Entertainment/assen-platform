import * as React from "react";
import type { Meta, StoryObj } from "@storybook/nextjs";
import { OTPInput } from "@/components/ui/otp-input";

const meta = {
  title: "Forms/OTPInput",
  component: OTPInput,
  parameters: { layout: "centered" },
} satisfies Meta<typeof OTPInput>;

export default meta;
type Story = StoryObj<typeof meta>;

function OTPDemo({ length }: { length?: number }) {
  const [value, setValue] = React.useState("");
  return (
    <div className="flex flex-col items-center gap-3">
      <OTPInput length={length} value={value} onChange={setValue} />
      <span className="text-caption text-on-surface-variant">입력: {value || "—"}</span>
    </div>
  );
}

export const SixDigit: Story = {
  name: "6자리",
  render: () => <OTPDemo />,
};

export const FourDigit: Story = {
  name: "4자리",
  render: () => <OTPDemo length={4} />,
};
