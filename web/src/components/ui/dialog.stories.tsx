import type { Meta, StoryObj } from "@storybook/nextjs";
import {
  Dialog,
  DialogTrigger,
  DialogClose,
  DialogContent,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";

const meta = {
  title: "Overlays/Dialog",
  component: Dialog,
  parameters: { layout: "centered" },
} satisfies Meta<typeof Dialog>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Confirm: Story = {
  name: "확인 다이얼로그",
  render: () => (
    <Dialog>
      <DialogTrigger asChild>
        <Button variant="outline">구독 해지</Button>
      </DialogTrigger>
      <DialogContent>
        <DialogTitle>구독을 해지할까요?</DialogTitle>
        <DialogDescription>다음 결제일부터 혜택이 중단됩니다.</DialogDescription>
        <div className="flex justify-end gap-2">
          <DialogClose asChild>
            <Button variant="outline">취소</Button>
          </DialogClose>
          <Button>해지</Button>
        </div>
      </DialogContent>
    </Dialog>
  ),
};
