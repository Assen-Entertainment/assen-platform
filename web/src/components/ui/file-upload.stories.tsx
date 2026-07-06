import * as React from "react";
import type { Meta, StoryObj } from "@storybook/nextjs";
import { FileUpload } from "@/components/ui/file-upload";

const meta = {
  title: "Forms/FileUpload",
  component: FileUpload,
  parameters: { layout: "padded" },
  argTypes: {
    label: { control: "text" },
    accept: { control: "text" },
    multiple: { control: "boolean" },
  },
  args: { onFiles: () => {}, accept: "image/*", multiple: true },
  render: (args) => (
    <div className="w-96 max-w-full">
      <FileUpload {...args} />
    </div>
  ),
} satisfies Meta<typeof FileUpload>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};

function PickedDemo() {
  const [names, setNames] = React.useState<string[]>([]);
  return (
    <div className="flex w-96 max-w-full flex-col gap-2">
      <FileUpload accept="image/*" multiple onFiles={(files) => setNames(files.map((f) => f.name))} />
      <span className="text-caption text-on-surface-variant">
        선택된 파일: {names.length ? names.join(", ") : "없음"}
      </span>
    </div>
  );
}

export const WithSelection: Story = {
  name: "선택 결과 표시",
  render: () => <PickedDemo />,
};
