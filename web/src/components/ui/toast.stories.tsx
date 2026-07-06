import type { Meta, StoryObj } from "@storybook/nextjs";
import { Toaster, useToast } from "@/components/ui/use-toast";
import { Button } from "@/components/ui/button";

const meta = {
  title: "Overlays/Toast",
  component: Toaster,
  parameters: { layout: "centered" },
} satisfies Meta<typeof Toaster>;

export default meta;
type Story = StoryObj<typeof meta>;

function ToastDemo() {
  const { toast } = useToast();
  return (
    <div className="flex gap-2">
      <Button onClick={() => toast({ title: "저장되었어요", description: "변경 사항이 반영되었습니다." })}>
        토스트 띄우기
      </Button>
      <Button variant="outline" onClick={() => toast({ title: "제목만 있는 토스트" })}>
        제목만
      </Button>
    </div>
  );
}

export const Default: Story = {
  render: () => (
    <Toaster>
      <ToastDemo />
    </Toaster>
  ),
};
