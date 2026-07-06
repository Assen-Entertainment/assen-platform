import * as React from "react";
import type { Meta, StoryObj } from "@storybook/nextjs";
import { CreatorHomeHeader } from "@/components/ui/creator-home-header";
import { creatorAccentVars } from "@/lib/creator-accent";

const meta = {
  title: "Commerce/CreatorHomeHeader",
  component: CreatorHomeHeader,
  parameters: { layout: "fullscreen" },
} satisfies Meta<typeof CreatorHomeHeader>;

export default meta;
type Story = StoryObj<typeof meta>;

function Demo(props: Partial<React.ComponentProps<typeof CreatorHomeHeader>>) {
  const [following, setFollowing] = React.useState(false);
  return (
    <div className="mx-auto max-w-xl p-4">
      <CreatorHomeHeader
        name="크리에이터 이름"
        handle="creator_handle"
        initial="크"
        followers={12400}
        posts={342}
        verified
        bio="일상을 그리는 일러스트레이터입니다. 매주 새로운 작업을 공유해요."
        following={following}
        onToggleFollow={() => setFollowing((v) => !v)}
        onGift={() => {}}
        followersHref="#"
        {...props}
      />
    </div>
  );
}

export const Default: Story = {
  render: () => <Demo />,
};

export const AccentWithGoal: Story = {
  name: "액센트 + 목표 진행",
  render: () => (
    <div style={creatorAccentVars("#E14B8A")}>
      <Demo accent goal={{ label: "다음 목표", value: 12400, max: 20000 }} />
    </div>
  ),
};
