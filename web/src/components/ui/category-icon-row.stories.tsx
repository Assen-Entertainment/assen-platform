import type { Meta, StoryObj } from "@storybook/nextjs";
import { CategoryIconRow } from "@/components/ui/category-icon-row";
import { IllustIcon, CosplayIcon, PhotoIcon, MusicIcon, GameIcon, WritingIcon } from "@/lib/icons";

const items = [
  { label: "일러스트", value: "illust", icon: <IllustIcon /> },
  { label: "코스프레", value: "cosplay", icon: <CosplayIcon /> },
  { label: "포토", value: "photo", icon: <PhotoIcon /> },
  { label: "음악", value: "music", icon: <MusicIcon /> },
  { label: "게임", value: "game", icon: <GameIcon /> },
  { label: "글", value: "writing", icon: <WritingIcon /> },
];

const meta = {
  title: "Navigation/CategoryIconRow",
  component: CategoryIconRow,
  parameters: { layout: "padded" },
  args: { items, onSelect: () => {} },
  render: (args) => (
    <div className="w-[24rem] max-w-full">
      <CategoryIconRow {...args} />
    </div>
  ),
} satisfies Meta<typeof CategoryIconRow>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};
