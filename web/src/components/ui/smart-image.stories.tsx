import type { Meta, StoryObj } from "@storybook/nextjs";
import { SmartImage } from "@/components/ui/smart-image";

/**
 * SmartImage — 원격(http/https) URL은 next/image(fill)로, 그 외(data:/상대)는 원시 img로 렌더.
 * 스토리는 도메인 설정이 필요 없는 비원격(data URI) 경로를 시연한다.
 */
const DATA_URI =
  "data:image/svg+xml;utf8," +
  encodeURIComponent(
    `<svg xmlns="http://www.w3.org/2000/svg" width="240" height="160"><defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#5A4DF0"/><stop offset="1" stop-color="#E14B8A"/></linearGradient></defs><rect width="240" height="160" fill="url(#g)"/></svg>`,
  );

const meta = {
  title: "Primitives/SmartImage",
  component: SmartImage,
  parameters: { layout: "centered" },
  argTypes: {
    alt: { control: "text" },
  },
  args: { src: DATA_URI, alt: "샘플 이미지", className: "size-40 rounded-lg object-cover" },
} satisfies Meta<typeof SmartImage>;

export default meta;
type Story = StoryObj<typeof meta>;

export const NonRemote: Story = {
  name: "비원격(data URI)",
};
