"use client";
import { ListItem, Switch, Divider, SectionHeader } from "@/components/ui";
import { usePersistentToggle } from "@/lib/use-persistent-state";

/** 알림 카테고리 정의 — 키는 localStorage 영속 식별자. */
const CATEGORIES: { key: string; title: string; subtitle: string; defaultOn: boolean }[] = [
  { key: "assen.notif.newPost", title: "새 포스트", subtitle: "구독한 크리에이터의 새 글", defaultOn: true },
  { key: "assen.notif.comment", title: "댓글·답글", subtitle: "내 글/댓글에 달린 반응", defaultOn: true },
  { key: "assen.notif.like", title: "좋아요", subtitle: "내 포스트에 눌린 좋아요", defaultOn: false },
  { key: "assen.notif.membership", title: "멤버십·구독", subtitle: "구독 갱신·혜택 안내", defaultOn: true },
  { key: "assen.notif.order", title: "주문·배송", subtitle: "결제·배송 상태 변경", defaultOn: true },
  { key: "assen.notif.marketing", title: "마케팅·이벤트", subtitle: "혜택·프로모션(선택)", defaultOn: false },
];

/** 알림 설정 상세 — W3. 카테고리별 스위치(localStorage 영속). */
export default function NotificationSettingsPage() {
  return (
    <div className="mx-auto flex max-w-2xl flex-col gap-4">
      <SectionHeader title="알림 설정" description="카테고리별로 알림을 켜고 끌 수 있어요" />
      <div className="overflow-hidden rounded-lg border border-outline">
        {CATEGORIES.map((c, i) => (
          <div key={c.key}>
            {i > 0 ? <Divider /> : null}
            <NotificationRow storageKey={c.key} title={c.title} subtitle={c.subtitle} defaultOn={c.defaultOn} />
          </div>
        ))}
      </div>
      <p className="text-caption text-on-surface-variant">설정은 이 브라우저에 저장돼요. (데모 — 실 알림 발송 미연동)</p>
    </div>
  );
}

function NotificationRow({
  storageKey,
  title,
  subtitle,
  defaultOn,
}: {
  storageKey: string;
  title: string;
  subtitle: string;
  defaultOn: boolean;
}) {
  const [on, setOn] = usePersistentToggle(storageKey, defaultOn);
  return (
    <ListItem
      title={title}
      subtitle={subtitle}
      trailing={<Switch aria-label={title} checked={on} onCheckedChange={setOn} />}
    />
  );
}
