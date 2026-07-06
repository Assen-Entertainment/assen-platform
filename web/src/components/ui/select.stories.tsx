import type { Meta, StoryObj } from "@storybook/nextjs";
import {
  Select,
  SelectTrigger,
  SelectValue,
  SelectContent,
  SelectItem,
} from "@/components/ui/select";

const meta = {
  title: "Forms/Select",
  component: Select,
  parameters: { layout: "centered" },
} satisfies Meta<typeof Select>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {
  render: () => (
    <Select defaultValue="latest">
      <SelectTrigger className="w-56">
        <SelectValue placeholder="정렬 기준" />
      </SelectTrigger>
      <SelectContent>
        <SelectItem value="latest">최신순</SelectItem>
        <SelectItem value="popular">인기순</SelectItem>
        <SelectItem value="priceAsc">가격 낮은순</SelectItem>
        <SelectItem value="priceDesc">가격 높은순</SelectItem>
      </SelectContent>
    </Select>
  ),
};

export const Placeholder: Story = {
  name: "미선택(placeholder)",
  render: () => (
    <Select>
      <SelectTrigger className="w-56">
        <SelectValue placeholder="카테고리 선택" />
      </SelectTrigger>
      <SelectContent>
        <SelectItem value="illust">일러스트</SelectItem>
        <SelectItem value="music">음악</SelectItem>
        <SelectItem value="goods">굿즈</SelectItem>
      </SelectContent>
    </Select>
  ),
};
