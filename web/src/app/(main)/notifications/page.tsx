import { getNotificationsPage } from "@/lib/api";
import { NotificationsView } from "./notifications-view";

/** Notifications — 서버에서 커서 Page(getNotificationsPage) 시드 → 클라 뷰(읽음·그룹핑·무한 로드). */
export default async function NotificationsPage() {
  const notifications = await getNotificationsPage();
  return <NotificationsView notifications={notifications} />;
}
