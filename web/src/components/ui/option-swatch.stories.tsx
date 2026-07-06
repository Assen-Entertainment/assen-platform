import * as React from "react";
import type { Meta, StoryObj } from "@storybook/nextjs";
import { OptionSwatch } from "@/components/ui/option-swatch";

const meta = {
  title: "Forms/OptionSwatch",
  component: OptionSwatch,
  parameters: { layout: "centered" },
  argTypes: {
    selected: { control: "boolean" },
    disabled: { control: "boolean" },
    children: { control: "text" },
  },
  args: { children: "A타입", selected: false, disabled: false },
} satisfies Meta<typeof OptionSwatch>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Playground: Story = {};

const OPTIONS = ["A타입", "B타입", "C타입", "D타입(품절)"];

function OptionGroup() {
  const [selected, setSelected] = React.useState("A타입");
  return (
    <div className="flex flex-wrap gap-2" role="group" aria-label="옵션 선택">
      {OPTIONS.map((o) => {
        const soldOut = o.includes("품절");
        return (
          <OptionSwatch
            key={o}
            selected={selected === o}
            disabled={soldOut}
            onClick={() => setSelected(o)}
          >
            {o}
          </OptionSwatch>
        );
      })}
    </div>
  );
}

export const SelectGroup: Story = {
  name: "옵션 그룹(품절 포함)",
  render: () => <OptionGroup />,
};
