import type { Meta, StoryObj } from "@storybook/nextjs";
import { BottomCTA } from "@/components/ui/bottom-cta";
import { Button } from "@/components/ui/button";
import { PriceLabel } from "@/components/ui/price-label";

const meta = {
  title: "Layout/BottomCTA",
  component: BottomCTA,
  // 화면 하단에 고정(fixed)되므로 fullscreen 캔버스에서 확인.
  parameters: { layout: "fullscreen" },
  argTypes: {
    persistent: { control: "boolean" },
  },
} satisfies Meta<typeof BottomCTA>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Checkout: Story = {
  name: "체크아웃 바",
  render: (args) => (
    <div className="min-h-[20rem] p-4 text-body-s text-on-surface-variant">
      상세 페이지 콘텐츠 영역 — 하단에 고정 CTA가 표시됩니다.
      <BottomCTA {...args} persistent>
        <PriceLabel amount={24000} className="shrink-0" />
        <Button size="lg" className="flex-1">
          바로 구매
        </Button>
      </BottomCTA>
    </div>
  ),
};
