import type { Meta, StoryObj } from "@storybook/nextjs";
import { Shelf } from "@/components/ui/shelf";
import { CreatorThumbCard } from "@/components/ui/creator-thumb-card";
import { TextLink } from "@/components/ui/text-link";

const meta = {
  title: "Layout/Shelf",
  component: Shelf,
  parameters: { layout: "padded" },
  argTypes: {
    title: { control: "text" },
    description: { control: "text" },
  },
  args: { title: "인기 크리에이터", description: "이번 주 가장 사랑받은 창작자" },
} satisfies Meta<typeof Shelf>;

export default meta;
type Story = StoryObj<typeof meta>;

const accents = ["#5A4DF0", "#E14B8A", "#0E9E9E", "#F2994A", "#7B61FF", "#2D9CDB"];

export const Default: Story = {
  render: (args) => (
    <div className="w-[40rem] max-w-full">
      <Shelf {...args} action={<TextLink href="#">전체 보기</TextLink>}>
        {accents.map((c, i) => (
          <CreatorThumbCard
            key={c}
            href="#"
            name={`크리에이터 ${i + 1}`}
            meta={`팔로워 ${(i + 1) * 1.2}k`}
            accentColor={c}
            className="w-40"
          />
        ))}
      </Shelf>
    </div>
  ),
};
