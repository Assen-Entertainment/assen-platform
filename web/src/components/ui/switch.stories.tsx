import type { Meta, StoryObj } from "@storybook/nextjs";
import { Switch } from "@/components/ui/switch";

const meta = {
  title: "Forms/Switch",
  component: Switch,
  parameters: { layout: "centered" },
} satisfies Meta<typeof Switch>;

export default meta;
type Story = StoryObj<typeof meta>;

export const States: Story = {
  render: () => (
    <div className="flex flex-col gap-3">
      <label className="flex items-center gap-3 text-body-m text-on-surface">
        <Switch /> 꺼짐
      </label>
      <label className="flex items-center gap-3 text-body-m text-on-surface">
        <Switch defaultChecked /> 켜짐
      </label>
      <label className="flex items-center gap-3 text-body-m text-on-surface opacity-[0.38]">
        <Switch disabled /> 비활성
      </label>
    </div>
  ),
};
