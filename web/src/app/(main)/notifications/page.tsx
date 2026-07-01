import { ListItem, EmptyState, Divider } from "@/components/ui";
import { HeartFilledIcon, CommentIcon, PersonIcon } from "@/lib/icons";

const NOTIFS = [
  { id: "n1", icon: <HeartFilledIcon className="size-5 text-error" />, title: "별빛 일러스트님이 회원님의 댓글을 좋아합니다", time: "3시간 전" },
  { id: "n2", icon: <PersonIcon className="size-5 text-primary" />, title: "토끼방송국님이 회원님을 팔로우했습니다", time: "어제" },
  { id: "n3", icon: <CommentIcon className="size-5 text-on-surface-variant" />, title: "새 댓글이 달렸습니다", time: "2일 전" },
];

export default function NotificationsPage() {
  return (
    <div className="mx-auto flex max-w-2xl flex-col gap-4">
      <h1 className="text-headline text-on-surface">알림</h1>
      {NOTIFS.length ? (
        <div className="overflow-hidden rounded-lg border border-outline">
          {NOTIFS.map((n, i) => (
            <div key={n.id}>
              {i > 0 ? <Divider /> : null}
              <ListItem
                leading={<span className="flex size-9 items-center justify-center rounded-full bg-surface-container-high">{n.icon}</span>}
                title={n.title}
                subtitle={n.time}
              />
            </div>
          ))}
        </div>
      ) : (
        <EmptyState title="알림이 없어요" description="새 소식이 오면 여기에 표시됩니다." />
      )}
    </div>
  );
}
