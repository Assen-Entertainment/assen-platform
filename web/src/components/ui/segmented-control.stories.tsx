import * as React from "react";
import type { Meta, StoryObj } from "@storybook/nextjs";
import { SegmentedControl } from "@/components/ui/segmented-control";

const meta = {
  title: "Navigation/SegmentedControl",
  component: SegmentedControl,
  parameters: { layout: "centered" },
} satisfies Meta<typeof SegmentedControl>;

export default meta;
type Story = StoryObj<typeof meta>;

function Demo({ options }: { options: { label: string; value: string }[] }) {
  const [value, setValue] = React.useState(options[0].value);
  return <SegmentedControl options={options} value={value} onValueChange={setValue} />;
}

export const TwoOptions: Story = {
  name: "2개 옵션",
  render: () => (
    <Demo
      options={[
        { label: "포스트", value: "posts" },
        { label: "굿즈", value: "goods" },
      ]}
    />
  ),
};

export const ThreeOptions: Story = {
  name: "3개 옵션",
  render: () => (
    <Demo
      options={[
        { label: "전체", value: "all" },
        { label: "이미지", value: "image" },
        { label: "동영상", value: "video" },
      ]}
    />
  ),
};
