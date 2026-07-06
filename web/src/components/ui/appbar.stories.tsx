import type { Meta, StoryObj } from "@storybook/nextjs";
import { AppBar } from "@/components/ui/appbar";
import { ChevronLeftIcon, MoreIcon, ShareIcon } from "@/lib/icons";

const meta = {
  title: "Layout/AppBar",
  component: AppBar,
  parameters: { layout: "fullscreen" },
  argTypes: {
    title: { control: "text" },
  },
  args: { title: "포스트 상세" },
  render: (args) => (
    <div className="w-[375px] max-w-full border-x border-outline">
      <AppBar
        {...args}
        leading={
          <button type="button" aria-label="뒤로" className="flex size-10 items-center justify-center text-on-surface [&>svg]:size-6">
            <ChevronLeftIcon />
          </button>
        }
      />
    </div>
  ),
} satisfies Meta<typeof AppBar>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};

export const WithActions: Story = {
  name: "우측 액션",
  render: (args) => (
    <div className="w-[375px] max-w-full border-x border-outline">
      <AppBar
        {...args}
        title="크리에이터"
        leading={
          <button type="button" aria-label="뒤로" className="flex size-10 items-center justify-center text-on-surface [&>svg]:size-6">
            <ChevronLeftIcon />
          </button>
        }
        trailing={
          <>
            <button type="button" aria-label="공유" className="flex size-10 items-center justify-center text-on-surface [&>svg]:size-6">
              <ShareIcon />
            </button>
            <button type="button" aria-label="더보기" className="flex size-10 items-center justify-center text-on-surface [&>svg]:size-6">
              <MoreIcon />
            </button>
          </>
        }
      />
    </div>
  ),
};
