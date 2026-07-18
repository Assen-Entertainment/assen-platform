import type { Meta, StoryObj } from "@storybook/nextjs";
import { PostCard } from "@/components/ui/post-card";

const meta = {
  title: "Feed/PostCard",
  component: PostCard,
  parameters: { layout: "centered" },
  args: {
    creatorName: "크리에이터 이름",
    creatorMeta: "@creator_handle · 3시간 전",
    avatarFallback: "C",
    verified: true,
    body: "새 포스트를 올렸어요.\n팬 여러분 응원 감사합니다!",
    likeCount: 128,
    commentCount: 12,
    liked: true,
  },
  render: (args) => (
    <div className="w-[32rem] max-w-full overflow-hidden rounded-lg border border-outline">
      <PostCard
        {...args}
        media={<div className="aspect-video w-full bg-surface-container-high" />}
      />
    </div>
  ),
} satisfies Meta<typeof PostCard>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Liked: Story = {};

export const TextOnly: Story = {
  name: "텍스트만",
  render: (args) => (
    <div className="w-[32rem] max-w-full overflow-hidden rounded-lg border border-outline">
      <PostCard {...args} media={undefined} liked={false} likeCount={12} />
    </div>
  ),
};
