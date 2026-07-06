import * as React from "react";
import type { Meta, StoryObj } from "@storybook/nextjs";
import { DatePicker } from "@/components/ui/date-picker";

const meta = {
  title: "Forms/DatePicker",
  component: DatePicker,
  // 팝오버가 아래로 펼쳐지도록 상단 여백 확보.
  parameters: { layout: "padded" },
} satisfies Meta<typeof DatePicker>;

export default meta;
type Story = StoryObj<typeof meta>;

function DatePickerDemo(props: React.ComponentProps<typeof DatePicker>) {
  const [date, setDate] = React.useState<Date | null>(null);
  return (
    <div className="flex flex-col gap-2 pb-80">
      <DatePicker {...props} value={date} onChange={setDate} />
      <span className="text-body-s text-on-surface-variant">
        선택: {date ? `${date.getFullYear()}년 ${date.getMonth() + 1}월 ${date.getDate()}일` : "없음"}
      </span>
    </div>
  );
}

export const Default: Story = {
  render: () => <DatePickerDemo aria-label="날짜 선택" />,
};

export const MinMax: Story = {
  name: "min/max 제한(7월)",
  render: () => (
    <DatePickerDemo
      aria-label="7월 한정 날짜"
      placeholder="7월만 선택 가능"
      min={new Date(2026, 6, 1)}
      max={new Date(2026, 6, 31)}
      defaultMonth={new Date(2026, 6, 1)}
    />
  ),
};
