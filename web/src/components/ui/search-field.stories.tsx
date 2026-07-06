import * as React from "react";
import type { Meta, StoryObj } from "@storybook/nextjs";
import { SearchField } from "@/components/ui/search-field";

const meta = {
  title: "Forms/SearchField",
  component: SearchField,
  parameters: { layout: "padded" },
  argTypes: {
    placeholder: { control: "text" },
    disabled: { control: "boolean" },
  },
  args: { placeholder: "크리에이터·굿즈 검색" },
  render: (args) => (
    <div className="w-80 max-w-full">
      <SearchField aria-label="검색" {...args} />
    </div>
  ),
} satisfies Meta<typeof SearchField>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};

function ControlledDemo() {
  const [q, setQ] = React.useState("");
  return (
    <div className="flex w-80 max-w-full flex-col gap-2">
      <SearchField aria-label="검색" value={q} onChange={(e) => setQ(e.target.value)} placeholder="입력해 보세요" />
      <span className="text-caption text-on-surface-variant">검색어: {q || "—"}</span>
    </div>
  );
}

export const Controlled: Story = {
  name: "제어형",
  render: () => <ControlledDemo />,
};
