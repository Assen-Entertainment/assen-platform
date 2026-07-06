import type { Meta, StoryObj } from "@storybook/nextjs";
import { Checkbox } from "@/components/ui/checkbox";

const meta = {
  title: "Forms/Checkbox",
  component: Checkbox,
  parameters: { layout: "centered" },
} satisfies Meta<typeof Checkbox>;

export default meta;
type Story = StoryObj<typeof meta>;

export const States: Story = {
  render: () => (
    <div className="flex flex-col gap-3">
      <label className="flex items-center gap-2 text-body-m text-on-surface">
        <Checkbox /> 미선택
      </label>
      <label className="flex items-center gap-2 text-body-m text-on-surface">
        <Checkbox defaultChecked /> 선택됨
      </label>
      <label className="flex items-center gap-2 text-body-m text-on-surface opacity-[0.38]">
        <Checkbox disabled /> 비활성
      </label>
      <label className="flex items-center gap-2 text-body-m text-on-surface">
        <Checkbox defaultChecked disabled /> 비활성(선택)
      </label>
    </div>
  ),
};
