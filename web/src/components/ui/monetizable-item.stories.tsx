import type { Meta, StoryObj } from "@storybook/nextjs";
import { MonetizableItem } from "@/components/ui/monetizable-item";

const meta = {
  title: "Commerce/MonetizableItem",
  component: MonetizableItem,
  parameters: { layout: "centered" },
  argTypes: {
    type: {
      control: "select",
      options: ["goods", "digital", "experience", "ticket", "coupon", "membership"],
    },
    title: { control: "text" },
    price: { control: "text" },
    meta: { control: "text" },
  },
  args: {
    type: "goods",
    title: "굿즈 상품명",
    price: "₩30,000",
    meta: "재고 12개 · 한정",
  },
  render: (args) => (
    <div className="w-56">
      <MonetizableItem {...args} />
    </div>
  ),
} satisfies Meta<typeof MonetizableItem>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Playground: Story = {};

export const Types: Story = {
  name: "타입별",
  render: () => (
    <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
      <MonetizableItem type="goods" title="굿즈 상품명" price="₩30,000" meta="재고 12개 · 한정" />
      <MonetizableItem type="digital" title="디지털 화보집" price="₩5,000" meta="다운로드 콘텐츠" />
      <MonetizableItem type="experience" title="포토카드 팬사인" price="₩12,000" meta="11/30 · 선착순 30" />
      <MonetizableItem type="coupon" title="10% 할인 쿠폰" price="₩3,000" meta="30일 유효" />
    </div>
  ),
};
