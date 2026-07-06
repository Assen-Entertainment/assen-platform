import type { Meta, StoryObj } from "@storybook/nextjs";
import {
  DropdownMenu,
  DropdownMenuTrigger,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
} from "@/components/ui/dropdown-menu";
import { Button } from "@/components/ui/button";

const meta = {
  title: "Overlays/DropdownMenu",
  component: DropdownMenu,
  parameters: { layout: "centered" },
} satisfies Meta<typeof DropdownMenu>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {
  render: () => (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="outline">메뉴</Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent>
        <DropdownMenuItem>수정</DropdownMenuItem>
        <DropdownMenuItem>공유</DropdownMenuItem>
        <DropdownMenuSeparator />
        <DropdownMenuItem destructive>삭제</DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  ),
};
