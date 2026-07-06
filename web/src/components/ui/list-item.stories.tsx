import type { Meta, StoryObj } from "@storybook/nextjs";
import { ListItem } from "@/components/ui/list-item";
import { Avatar } from "@/components/ui/avatar";
import { Switch } from "@/components/ui/switch";
import { Badge } from "@/components/ui/badge";
import { SettingsIcon } from "@/lib/icons";

const meta = {
  title: "Primitives/ListItem",
  component: ListItem,
  parameters: { layout: "padded" },
  argTypes: {
    title: { control: "text" },
    subtitle: { control: "text" },
    showChevron: { control: "boolean" },
  },
  args: { title: "알림 설정", subtitle: "푸시·이메일 수신 설정", showChevron: true },
  render: (args) => (
    <div className="w-80 overflow-hidden rounded-lg border border-outline">
      <ListItem {...args} leading={<SettingsIcon className="size-6 text-on-surface-variant" />} />
    </div>
  ),
} satisfies Meta<typeof ListItem>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};

export const List: Story = {
  name: "리스트(구분선)",
  render: () => (
    <div className="w-80 divide-y divide-outline overflow-hidden rounded-lg border border-outline">
      <ListItem
        leading={<Avatar fallback="이" size="sm" tone="creator-1" />}
        title="크리에이터 이름"
        subtitle="@creator_handle"
        trailing={<Badge variant="primary">팔로잉</Badge>}
      />
      <ListItem title="다크 모드" subtitle="시스템 설정 따르기" trailing={<Switch defaultChecked aria-label="다크 모드" />} />
      <ListItem title="결제 수단 관리" subtitle="카드·계좌 등록" showChevron />
      <ListItem title="고객센터" showChevron />
    </div>
  ),
};
