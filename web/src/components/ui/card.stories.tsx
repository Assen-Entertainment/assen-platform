import type { Meta, StoryObj } from "@storybook/nextjs";
import { Card, CardBody } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";

const meta = {
  title: "Primitives/Card",
  component: Card,
  parameters: { layout: "centered" },
} satisfies Meta<typeof Card>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {
  render: () => (
    <Card className="w-80">
      <CardBody>
        <div className="flex items-center justify-between">
          <h3 className="text-title-m text-on-surface">카드 제목</h3>
          <Badge variant="primary">인기</Badge>
        </div>
        <p className="text-body-s text-on-surface-variant">
          surface + outline + radius.lg 로 구성된 기본 카드. border-first elevation.
        </p>
        <Button size="sm" className="mt-2 self-start">자세히</Button>
      </CardBody>
    </Card>
  ),
};
