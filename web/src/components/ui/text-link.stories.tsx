import type { Meta, StoryObj } from "@storybook/nextjs";
import { TextLink } from "@/components/ui/text-link";

const meta = {
  title: "Primitives/TextLink",
  component: TextLink,
  parameters: { layout: "centered" },
  argTypes: {
    children: { control: "text" },
    href: { control: "text" },
  },
  args: { children: "이용약관 보기", href: "#" },
} satisfies Meta<typeof TextLink>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Playground: Story = {};

export const InlineParagraph: Story = {
  name: "본문 내 링크",
  render: () => (
    <p className="max-w-sm text-body-m text-on-surface">
      결제를 진행하면 <TextLink href="#">이용약관</TextLink> 및{" "}
      <TextLink href="#">개인정보처리방침</TextLink>에 동의하는 것으로 간주됩니다.
    </p>
  ),
};
