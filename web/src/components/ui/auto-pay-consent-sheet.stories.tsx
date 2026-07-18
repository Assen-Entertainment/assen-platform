import * as React from "react";
import type { Meta, StoryObj } from "@storybook/nextjs";
import { AutoPayConsentSheet } from "@/components/ui/auto-pay-consent-sheet";

const meta = {
  title: "Overlays/AutoPayConsentSheet",
  component: AutoPayConsentSheet,
  parameters: { layout: "padded" },
} satisfies Meta<typeof AutoPayConsentSheet>;

export default meta;
type Story = StoryObj<typeof meta>;

function Demo({ summary }: { summary?: string }) {
  const [checked, setChecked] = React.useState(false);
  return (
    <div className="w-96 max-w-full">
      <AutoPayConsentSheet checked={checked} onCheckedChange={setChecked} summary={summary} />
    </div>
  );
}

export const Default: Story = {
  render: () => <Demo />,
};

export const WithSummary: Story = {
  name: "결제 요약 포함",
  render: () => <Demo summary="다음 결제일 2026-08-06 · 월 9,900원" />,
};
