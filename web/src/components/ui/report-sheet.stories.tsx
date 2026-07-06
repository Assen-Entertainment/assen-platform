import * as React from "react";
import type { Meta, StoryObj } from "@storybook/nextjs";
import { ReportSheet } from "@/components/ui/report-sheet";
import { Button } from "@/components/ui/button";

const meta = {
  title: "Overlays/ReportSheet",
  component: ReportSheet,
  parameters: { layout: "centered" },
} satisfies Meta<typeof ReportSheet>;

export default meta;
type Story = StoryObj<typeof meta>;

function Demo() {
  const [open, setOpen] = React.useState(false);
  return (
    <>
      <Button variant="outline" onClick={() => setOpen(true)}>
        신고하기
      </Button>
      <ReportSheet open={open} onOpenChange={setOpen} onSubmit={() => {}} />
    </>
  );
}

export const Default: Story = {
  name: "신고 시트",
  render: () => <Demo />,
};
