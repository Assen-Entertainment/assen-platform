import type { Meta, StoryObj } from "@storybook/nextjs";
import { Breadcrumb } from "@/components/ui/breadcrumb";

const meta = {
  title: "Navigation/Breadcrumb",
  component: Breadcrumb,
  parameters: { layout: "padded" },
  args: {
    items: [
      { label: "홈", href: "/" },
      { label: "스토어", href: "/store" },
      { label: "일러스트", href: "/store/illust" },
      { label: "봄 한정 아트북" },
    ],
  },
} satisfies Meta<typeof Breadcrumb>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};

export const TwoLevel: Story = {
  name: "2단계",
  args: {
    items: [
      { label: "마이페이지", href: "/me" },
      { label: "주문 내역" },
    ],
  },
};
