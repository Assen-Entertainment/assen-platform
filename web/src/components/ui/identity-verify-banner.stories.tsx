import type { Meta, StoryObj } from "@storybook/nextjs";
import { IdentityVerifyBanner } from "@/components/ui/identity-verify-banner";
import { Button } from "@/components/ui/button";

const meta = {
  title: "Notices/IdentityVerifyBanner",
  component: IdentityVerifyBanner,
  parameters: { layout: "padded" },
  argTypes: {
    verified: { control: "boolean" },
  },
  args: { verified: false },
  render: (args) => (
    <div className="w-[28rem] max-w-full">
      <IdentityVerifyBanner
        {...args}
        action={
          <Button size="sm" variant="outline">
            인증하기
          </Button>
        }
      />
    </div>
  ),
} satisfies Meta<typeof IdentityVerifyBanner>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Unverified: Story = {
  name: "미인증",
};

export const Verified: Story = {
  name: "인증 완료",
  args: { verified: true },
};
