import type { Meta, StoryObj } from "@storybook/nextjs";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";

const meta = {
  title: "Navigation/Tabs",
  component: Tabs,
  parameters: { layout: "padded" },
} satisfies Meta<typeof Tabs>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {
  render: () => (
    <Tabs defaultValue="posts" className="w-full max-w-md">
      <TabsList>
        <TabsTrigger value="posts">포스트</TabsTrigger>
        <TabsTrigger value="store">스토어</TabsTrigger>
        <TabsTrigger value="membership">멤버십</TabsTrigger>
      </TabsList>
      <TabsContent value="posts" className="p-4 text-body-m text-on-surface">포스트 탭 내용</TabsContent>
      <TabsContent value="store" className="p-4 text-body-m text-on-surface">스토어 탭 내용</TabsContent>
      <TabsContent value="membership" className="p-4 text-body-m text-on-surface">멤버십 탭 내용</TabsContent>
    </Tabs>
  ),
};
