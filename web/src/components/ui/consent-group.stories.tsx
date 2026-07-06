import * as React from "react";
import type { Meta, StoryObj } from "@storybook/nextjs";
import { ConsentGroup, type ConsentItem } from "@/components/ui/consent-group";

const ITEMS: ConsentItem[] = [
  { id: "tos", label: "이용약관 동의", required: true },
  { id: "priv", label: "개인정보 처리방침", required: true },
  { id: "mkt", label: "마케팅 정보 수신 (선택)" },
];

const meta = {
  title: "Forms/ConsentGroup",
  component: ConsentGroup,
  parameters: { layout: "centered" },
} satisfies Meta<typeof ConsentGroup>;

export default meta;
type Story = StoryObj<typeof meta>;

function ConsentDemo() {
  const [value, setValue] = React.useState<string[]>(["tos"]);
  return <ConsentGroup className="w-80" items={ITEMS} value={value} onChange={setValue} />;
}

export const Default: Story = {
  render: () => <ConsentDemo />,
};
