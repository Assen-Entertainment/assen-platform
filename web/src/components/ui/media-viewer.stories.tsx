import * as React from "react";
import type { Meta, StoryObj } from "@storybook/nextjs";
import { MediaViewer } from "@/components/ui/media-viewer";
import { Button } from "@/components/ui/button";

const meta = {
  title: "Overlays/MediaViewer",
  component: MediaViewer,
  parameters: { layout: "fullscreen" },
} satisfies Meta<typeof MediaViewer>;

export default meta;
type Story = StoryObj<typeof meta>;

function Demo() {
  const [open, setOpen] = React.useState(false);
  return (
    <div className="p-6">
      <Button onClick={() => setOpen(true)}>미디어 크게 보기</Button>
      <MediaViewer
        open={open}
        onClose={() => setOpen(false)}
        seed="post-hero-2026"
        caption="봄 신작 일러스트 — 미리보기"
        alt="봄 신작 일러스트"
      />
    </div>
  );
}

export const Default: Story = {
  render: () => <Demo />,
};
