import type { Meta, StoryObj } from "@storybook/nextjs";
import {
  Sheet,
  SheetTrigger,
  SheetClose,
  SheetContent,
  SheetTitle,
  SheetDescription,
} from "@/components/ui/sheet";
import { Button } from "@/components/ui/button";

const meta = {
  title: "Overlays/Sheet",
  component: Sheet,
  parameters: { layout: "centered" },
} satisfies Meta<typeof Sheet>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Bottom: Story = {
  name: "하단(모바일)",
  render: () => (
    <Sheet>
      <SheetTrigger asChild>
        <Button variant="outline">정렬 옵션</Button>
      </SheetTrigger>
      <SheetContent side="bottom">
        <SheetTitle>정렬 옵션</SheetTitle>
        <SheetDescription>목록 정렬 기준을 선택하세요.</SheetDescription>
        <div className="flex flex-col gap-1">
          <SheetClose asChild><Button variant="ghost" className="justify-start">최신순</Button></SheetClose>
          <SheetClose asChild><Button variant="ghost" className="justify-start">인기순</Button></SheetClose>
          <SheetClose asChild><Button variant="ghost" className="justify-start">가격순</Button></SheetClose>
        </div>
      </SheetContent>
    </Sheet>
  ),
};

export const Right: Story = {
  name: "우측(데스크톱)",
  render: () => (
    <Sheet>
      <SheetTrigger asChild>
        <Button variant="outline">필터</Button>
      </SheetTrigger>
      <SheetContent side="right">
        <SheetTitle>필터</SheetTitle>
        <SheetDescription>우측 사이드 시트(웹 데스크톱).</SheetDescription>
        <SheetClose asChild><Button className="mt-2">적용</Button></SheetClose>
      </SheetContent>
    </Sheet>
  ),
};
