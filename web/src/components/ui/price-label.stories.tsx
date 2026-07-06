import type { Meta, StoryObj } from "@storybook/nextjs";
import { PriceLabel } from "@/components/ui/price-label";

const meta = {
  title: "Primitives/PriceLabel",
  component: PriceLabel,
  parameters: { layout: "centered" },
  argTypes: {
    amount: { control: "number" },
    suffix: { control: "text" },
    originalAmount: { control: "number" },
    discountPercent: { control: "number" },
    currency: { control: "text" },
  },
  args: { amount: 30000 },
} satisfies Meta<typeof PriceLabel>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Playground: Story = {};

export const Subscription: Story = {
  name: "구독가(접미)",
  args: { amount: 9900, suffix: "/월" },
};

export const Discounted: Story = {
  name: "할인(원가 취소선)",
  args: { amount: 5000, originalAmount: 10000, discountPercent: 50 },
};
