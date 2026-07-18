import type { Meta, StoryObj } from "@storybook/nextjs";
import { TextField } from "@/components/ui/textfield";

const meta = {
  title: "Forms/TextField",
  component: TextField,
  parameters: { layout: "centered" },
  argTypes: {
    label: { control: "text" },
    placeholder: { control: "text" },
    helperText: { control: "text" },
    errorText: { control: "text" },
    error: { control: "boolean" },
    disabled: { control: "boolean" },
  },
  args: {
    label: "이메일",
    placeholder: "you@assen.kr",
    error: false,
    disabled: false,
  },
  render: (args) => (
    <div className="w-72">
      <TextField {...args} />
    </div>
  ),
} satisfies Meta<typeof TextField>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Playground: Story = {};

export const WithHelper: Story = {
  name: "도움말",
  args: { helperText: "회원가입에 사용한 이메일을 입력하세요." },
};

export const Error: Story = {
  args: { error: true, errorText: "필수 항목입니다." },
};

export const Disabled: Story = {
  args: { disabled: true, value: "잠긴 값" },
};
