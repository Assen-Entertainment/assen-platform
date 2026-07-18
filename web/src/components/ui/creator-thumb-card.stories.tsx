import type { Meta, StoryObj } from "@storybook/nextjs";
import { CreatorThumbCard } from "@/components/ui/creator-thumb-card";

const meta = {
  title: "Commerce/CreatorThumbCard",
  component: CreatorThumbCard,
  parameters: { layout: "centered" },
  argTypes: {
    name: { control: "text" },
    meta: { control: "text" },
    accentColor: { control: "color" },
  },
  args: {
    name: "크리에이터 이름",
    meta: "일러스트 · 팔로워 1.2k",
    href: "#",
  },
  render: (args) => (
    <div className="w-44">
      <CreatorThumbCard {...args} />
    </div>
  ),
} satisfies Meta<typeof CreatorThumbCard>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};

export const WithAccent: Story = {
  name: "크리에이터 액센트",
  args: { accentColor: "#E14B8A", meta: "코스프레 · 팔로워 8.4k" },
};

export const Grid: Story = {
  name: "그리드",
  render: () => (
    <div className="grid w-[28rem] grid-cols-3 gap-4">
      <CreatorThumbCard href="#" name="일러스트레이터" meta="팔로워 1.2k" accentColor="#5A4DF0" />
      <CreatorThumbCard href="#" name="포토그래퍼" meta="팔로워 3.1k" accentColor="#0E9E9E" />
      <CreatorThumbCard href="#" name="뮤지션" meta="팔로워 900" accentColor="#F2994A" />
    </div>
  ),
};
