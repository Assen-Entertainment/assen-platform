import * as React from "react";
import type { Meta, StoryObj } from "@storybook/nextjs";
import { Calendar } from "@/components/ui/calendar";

const meta = {
  title: "Forms/Calendar",
  component: Calendar,
  parameters: { layout: "centered" },
} satisfies Meta<typeof Calendar>;

export default meta;
type Story = StoryObj<typeof meta>;

function CalendarDemo(props: React.ComponentProps<typeof Calendar>) {
  const [value, setValue] = React.useState<Date | null>(null);
  return (
    <div className="flex flex-col items-center gap-2">
      <div className="rounded-lg border border-outline">
        <Calendar {...props} value={value} onSelect={setValue} />
      </div>
      <span className="text-caption text-on-surface-variant">
        선택: {value ? `${value.getFullYear()}년 ${value.getMonth() + 1}월 ${value.getDate()}일` : "없음"}
      </span>
    </div>
  );
}

export const Default: Story = {
  render: () => <CalendarDemo aria-label="날짜 선택" defaultMonth={new Date(2026, 6, 1)} />,
};

export const MinMax: Story = {
  name: "min/max 제한(7월)",
  render: () => (
    <CalendarDemo
      aria-label="7월 한정 날짜"
      min={new Date(2026, 6, 1)}
      max={new Date(2026, 6, 31)}
      defaultMonth={new Date(2026, 6, 1)}
    />
  ),
};
