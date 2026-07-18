import type { Meta, StoryObj } from "@storybook/nextjs";
import {
  Accordion,
  AccordionItem,
  AccordionTrigger,
  AccordionContent,
} from "@/components/ui/accordion";

const meta = {
  title: "Navigation/Accordion",
  component: Accordion,
  parameters: { layout: "padded" },
} satisfies Meta<typeof Accordion>;

export default meta;
type Story = StoryObj<typeof meta>;

export const FAQ: Story = {
  name: "FAQ",
  render: () => (
    <Accordion type="single" collapsible className="w-full max-w-md">
      <AccordionItem value="a">
        <AccordionTrigger>구독은 언제든 해지할 수 있나요?</AccordionTrigger>
        <AccordionContent>네, 마이페이지에서 즉시 해지할 수 있고 남은 기간 동안 혜택이 유지됩니다.</AccordionContent>
      </AccordionItem>
      <AccordionItem value="b">
        <AccordionTrigger>결제 수단은 무엇을 지원하나요?</AccordionTrigger>
        <AccordionContent>신용/체크카드와 간편결제를 지원합니다.</AccordionContent>
      </AccordionItem>
      <AccordionItem value="c">
        <AccordionTrigger>환불 정책이 궁금해요.</AccordionTrigger>
        <AccordionContent>디지털 콘텐츠는 열람 전에 한해 환불이 가능합니다.</AccordionContent>
      </AccordionItem>
    </Accordion>
  ),
};
