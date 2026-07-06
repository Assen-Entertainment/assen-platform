import * as React from "react";
import type { Meta, StoryObj } from "@storybook/nextjs";
import { GiftSheet } from "@/components/ui/gift-sheet";
import { Button } from "@/components/ui/button";

const meta = {
  title: "Overlays/GiftSheet",
  component: GiftSheet,
  parameters: { layout: "centered" },
} satisfies Meta<typeof GiftSheet>;

export default meta;
type Story = StoryObj<typeof meta>;

function Demo() {
  const [open, setOpen] = React.useState(false);
  return (
    <>
      <Button onClick={() => setOpen(true)}>후원하기</Button>
      <GiftSheet open={open} onOpenChange={setOpen} creatorName="크리에이터" />
    </>
  );
}

export const Default: Story = {
  name: "후원 시트(mock)",
  render: () => <Demo />,
};
