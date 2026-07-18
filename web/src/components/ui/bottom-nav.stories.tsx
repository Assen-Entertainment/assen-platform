import type { Meta, StoryObj } from "@storybook/nextjs";
import { BottomNav } from "@/components/ui/bottom-nav";
import { HomeIcon, FeedIcon, StoreIcon, BellIcon, PersonIcon } from "@/lib/icons";

const items = [
  { icon: <HomeIcon />, label: "홈", href: "/" },
  { icon: <FeedIcon />, label: "피드", href: "/feed" },
  { icon: <StoreIcon />, label: "스토어", href: "/store" },
  { icon: <BellIcon />, label: "알림", href: "/notifications" },
  { icon: <PersonIcon />, label: "마이", href: "/me" },
];

const meta = {
  title: "Layout/BottomNav",
  component: BottomNav,
  parameters: { layout: "fullscreen" },
  args: { items, activeHref: "/" },
  render: (args) => (
    <div className="w-[375px] max-w-full border-x border-outline">
      <BottomNav {...args} />
    </div>
  ),
} satisfies Meta<typeof BottomNav>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};

export const StoreActive: Story = {
  name: "스토어 활성",
  args: { activeHref: "/store" },
};
