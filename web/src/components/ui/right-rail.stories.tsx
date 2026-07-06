import type { Meta, StoryObj } from "@storybook/nextjs";
import { RightRail } from "@/components/ui/right-rail";
import { SectionHeader } from "@/components/ui/section-header";
import { CreatorThumbCard } from "@/components/ui/creator-thumb-card";

const meta = {
  title: "Layout/RightRail",
  component: RightRail,
  // lg+ 에서만 표시되므로 데스크톱 뷰포트에서 확인.
  parameters: { layout: "fullscreen", viewport: { defaultViewport: "desktop" } },
} satisfies Meta<typeof RightRail>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {
  render: () => (
    <div className="flex min-h-[24rem] justify-end">
      <RightRail>
        <SectionHeader as="h3" title="추천 크리에이터" />
        <div className="flex flex-col gap-3">
          <CreatorThumbCard href="#" name="일러스트레이터" meta="팔로워 1.2k" accentColor="#5A4DF0" />
          <CreatorThumbCard href="#" name="포토그래퍼" meta="팔로워 3.1k" accentColor="#0E9E9E" />
        </div>
      </RightRail>
    </div>
  ),
};
