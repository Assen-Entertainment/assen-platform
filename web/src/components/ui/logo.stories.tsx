import type { Meta, StoryObj } from "@storybook/nextjs";
import { Logo } from "@/components/ui/logo";

/**
 * Logo — Assen 브랜드 로크업(플레이스홀더). 최종 브랜딩(E9) 확정 시 이 컴포넌트만 교체.
 * 마크(상승하는 A 모노그램·gradient.brand 타일) + Pretendard 워드마크.
 */
const meta = {
  title: "Brand/Logo",
  component: Logo,
  parameters: { layout: "centered" },
  argTypes: {
    variant: { control: "inline-radio", options: ["full", "mark", "wordmark"] },
    size: { control: "inline-radio", options: ["sm", "md", "lg"] },
    mono: { control: "boolean" },
  },
  args: { variant: "full", size: "md", mono: false },
} satisfies Meta<typeof Logo>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Playground: Story = {};

export const Variants: Story = {
  name: "변형",
  render: () => (
    <div className="flex flex-col items-start gap-5">
      <Logo variant="full" size="lg" />
      <Logo variant="full" size="md" />
      <Logo variant="mark" size="md" />
      <Logo variant="wordmark" size="md" />
    </div>
  ),
};

export const OnColor: Story = {
  name: "컬러 배경(mono)",
  render: () => (
    <div
      className="flex items-center gap-4 rounded-xl px-6 py-5 text-white"
      style={{ backgroundImage: "var(--gradient-brand)" }}
    >
      <Logo variant="full" size="lg" mono />
    </div>
  ),
};
