import type { Meta, StoryObj } from "@storybook/nextjs";
import { PaymentIcon } from "@/components/ui/payment-icon";

const meta = {
  title: "Primitives/PaymentIcon",
  component: PaymentIcon,
  parameters: { layout: "centered" },
  argTypes: {
    method: { control: "inline-radio", options: ["card", "bank", "pay", "point"] },
    showLabel: { control: "boolean" },
  },
  args: { method: "card", showLabel: true },
} satisfies Meta<typeof PaymentIcon>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Playground: Story = {};

export const AllMethods: Story = {
  name: "결제수단 전체",
  render: () => (
    <div className="flex flex-col items-start gap-2">
      <PaymentIcon method="card" showLabel />
      <PaymentIcon method="bank" showLabel />
      <PaymentIcon method="pay" showLabel />
      <PaymentIcon method="point" showLabel />
    </div>
  ),
};

export const BadgeOnly: Story = {
  name: "배지만(라벨 숨김)",
  render: () => (
    <div className="flex items-center gap-2">
      <PaymentIcon method="card" />
      <PaymentIcon method="bank" />
      <PaymentIcon method="pay" />
      <PaymentIcon method="point" />
    </div>
  ),
};
