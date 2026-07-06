import type { Meta, StoryObj } from "@storybook/nextjs";
import { Sidebar } from "@/components/ui/sidebar";
import { HomeIcon, FeedIcon, StoreIcon, BellIcon, SettingsIcon } from "@/lib/icons";

const items = [
  { icon: <HomeIcon />, label: "홈", href: "/" },
  { icon: <FeedIcon />, label: "피드", href: "/feed" },
  { icon: <StoreIcon />, label: "스토어", href: "/store" },
  { icon: <BellIcon />, label: "알림", href: "/notifications" },
  { icon: <SettingsIcon />, label: "설정", href: "/settings" },
];

const meta = {
  title: "Layout/Sidebar",
  component: Sidebar,
  parameters: { layout: "fullscreen" },
  args: { items, activeHref: "/feed" },
  render: (args) => (
    <div className="h-[28rem]">
      <Sidebar {...args} brand={<span className="text-title-l font-bold text-primary">Assen</span>} />
    </div>
  ),
} satisfies Meta<typeof Sidebar>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};

export const HomeActive: Story = {
  name: "홈 활성",
  args: { activeHref: "/" },
};
