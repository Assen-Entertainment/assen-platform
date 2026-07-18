import * as React from "react";
import type { Meta, StoryObj } from "@storybook/nextjs";
import { TextArea } from "@/components/ui/text-area";

const meta = {
  title: "Forms/TextArea",
  component: TextArea,
  parameters: { layout: "padded" },
  argTypes: {
    label: { control: "text" },
    helperText: { control: "text" },
    error: { control: "boolean" },
    errorText: { control: "text" },
    disabled: { control: "boolean" },
  },
  args: {
    label: "소개",
    helperText: "프로필에 표시될 자기소개를 적어주세요.",
    placeholder: "예) 일상을 그리는 일러스트레이터입니다.",
  },
  render: (args) => (
    <div className="w-80 max-w-full">
      <TextArea {...args} />
    </div>
  ),
} satisfies Meta<typeof TextArea>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};

export const Error: Story = {
  name: "오류",
  args: { error: true, errorText: "10자 이상 입력해 주세요.", label: "소개" },
};

function CountDemo() {
  const [value, setValue] = React.useState("");
  return (
    <div className="w-80 max-w-full">
      <TextArea
        label="응원 메시지"
        placeholder="크리에이터에게 남길 한마디"
        value={value}
        onChange={(e) => setValue(e.target.value)}
        maxLength={100}
        showCount
      />
    </div>
  );
}

export const WithCounter: Story = {
  name: "글자 수 카운터",
  render: () => <CountDemo />,
};
