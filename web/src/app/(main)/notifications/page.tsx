import { getNotifications } from "@/lib/api";
import { NotificationsView } from "./notifications-view";

/** Notifications — 서버 fetch(mock) → 클라 뷰(읽음 상태·그룹핑·라우팅). */
export default async function NotificationsPage() {
  const notifications = await getNotifications();
  return <NotificationsView notifications={notifications} />;
}
