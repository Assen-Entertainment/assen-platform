import * as React from "react";
import type { Meta, StoryObj } from "@storybook/nextjs";
import { QuantityStepper } from "@/components/ui/quantity-stepper";

const meta = {
  title: "Forms/QuantityStepper",
  component: QuantityStepper,
  parameters: { layout: "centered" },
} satisfies Meta<typeof QuantityStepper>;

export default meta;
type Story = StoryObj<typeof meta>;

function Demo({ min, max, initial = 1 }: { min?: number; max?: number; initial?: number }) {
  const [value, setValue] = React.useState(initial);
  return <QuantityStepper value={value} min={min} max={max} onChange={setValue} />;
}

export const Default: Story = {
  render: () => <Demo />,
};

export const Limited: Story = {
  name: "재고 한정(1~5)",
  render: () => <Demo min={1} max={5} initial={5} />,
};
