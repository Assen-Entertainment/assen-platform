import type { Meta, StoryObj } from "@storybook/nextjs";
import { TermsLinkFooter } from "@/components/ui/terms-link-footer";

const meta = {
  title: "Notices/TermsLinkFooter",
  component: TermsLinkFooter,
  parameters: { layout: "padded" },
} satisfies Meta<typeof TermsLinkFooter>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};

export const InConsentFlow: Story = {
  name: "동의 흐름 하단",
  render: () => (
    <div className="flex w-96 max-w-full flex-col gap-3">
      <p className="text-body-s text-on-surface-variant">
        가입을 진행하면 아래 정책에 동의하는 것으로 간주됩니다.
      </p>
      <TermsLinkFooter />
    </div>
  ),
};
