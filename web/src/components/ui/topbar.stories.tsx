import type { Meta, StoryObj } from "@storybook/nextjs";
import { TopBar } from "@/components/ui/topbar";
import { SearchField } from "@/components/ui/search-field";
import { Button } from "@/components/ui/button";
import { Avatar } from "@/components/ui/avatar";
import { BellIcon } from "@/lib/icons";

const meta = {
  title: "Layout/TopBar",
  component: TopBar,
  parameters: { layout: "fullscreen" },
} satisfies Meta<typeof TopBar>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {
  render: () => (
    <TopBar
      logo={<span className="text-title-l font-bold text-primary">Assen</span>}
      search={<SearchField className="w-full max-w-md" placeholder="크리에이터·굿즈 검색" />}
      actions={
        <>
          <button type="button" aria-label="알림" className="flex size-10 items-center justify-center text-on-surface-variant [&>svg]:size-6">
            <BellIcon />
          </button>
          <Button size="sm">크리에이터 되기</Button>
          <Avatar fallback="나" size="sm" tone="creator-2" />
        </>
      }
    />
  ),
};

export const SearchOnly: Story = {
  name: "검색 중심",
  render: () => (
    <TopBar
      search={<SearchField className="w-full max-w-md" placeholder="검색" />}
      actions={<Avatar fallback="나" size="sm" tone="creator-3" />}
    />
  ),
};
