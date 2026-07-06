import * as React from "react";
import type { Meta, StoryObj } from "@storybook/nextjs";
import { Chip } from "@/components/ui/chip";

const meta = {
  title: "Primitives/Chip",
  component: Chip,
  parameters: { layout: "centered" },
  argTypes: {
    selected: { control: "boolean" },
    disabled: { control: "boolean" },
    children: { control: "text" },
  },
  args: { children: "일러스트", selected: false, disabled: false },
} satisfies Meta<typeof Chip>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Playground: Story = {};

export const States: Story = {
  name: "상태",
  render: () => (
    <div className="flex flex-wrap items-center gap-2">
      <Chip>미선택</Chip>
      <Chip selected>선택됨</Chip>
      <Chip disabled>비활성</Chip>
    </div>
  ),
};

const CATEGORIES = ["전체", "일러스트", "코스프레", "포토", "음악"];

function FilterRow() {
  const [active, setActive] = React.useState("일러스트");
  return (
    <div className="flex flex-wrap gap-2" role="group" aria-label="카테고리 필터">
      {CATEGORIES.map((c) => (
        <Chip key={c} selected={active === c} onClick={() => setActive(c)}>
          {c}
        </Chip>
      ))}
    </div>
  );
}

export const FilterGroup: Story = {
  name: "필터 그룹(단일 선택)",
  render: () => <FilterRow />,
};
