"use client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ListItem, Switch, Divider } from "@/components/ui";
import { useTheme } from "@/components/theme-provider";
import { useSession } from "@/lib/session";

/** Settings — 설정. 다크모드 + 로그아웃 + 서브라우트 배선.
 *  ※알림(푸시 카테고리)·마케팅 수신은 /settings/notifications 단일 소유 — 여기서 중복 토글하지 않는다
 *  (기존 localStorage "푸시 알림"·"마케팅 수신"은 상세 페이지와 상태가 갈리던 blindspot #7/#8이라 제거). */
export default function SettingsPage() {
  const router = useRouter();
  const { resolvedTheme, setTheme } = useTheme();
  const { logout } = useSession();

  const onLogout = () => {
    logout();
    router.push("/discovery");
  };

  return (
    <div className="mx-auto flex max-w-4xl flex-col gap-4">
      <h1 className="text-headline text-on-surface">설정</h1>
      <div className="overflow-hidden rounded-lg border border-outline">
        <ListItem
          title="다크 모드"
          subtitle="어두운 테마"
          trailing={
            <Switch
              aria-label="다크 모드"
              checked={resolvedTheme === "dark"}
              onCheckedChange={(v) => setTheme(v ? "dark" : "light")}
            />
          }
        />
        <Divider />
        <Link href="/settings/notifications" className="block transition-colors hover:bg-surface-container-high">
          <ListItem title="알림 설정" subtitle="푸시·마케팅 등 카테고리별 상세 설정" showChevron />
        </Link>
        <Divider />
        <Link href="/settings/account" className="block transition-colors hover:bg-surface-container-high">
          <ListItem title="계정" subtitle="이메일·비밀번호·탈퇴" showChevron />
        </Link>
        <Divider />
        <Link href="/settings/payments" className="block transition-colors hover:bg-surface-container-high">
          <ListItem title="결제 수단" subtitle="카드·간편결제 관리" showChevron />
        </Link>
        <Divider />
        <Link href="/settings/blocked" className="block transition-colors hover:bg-surface-container-high">
          <ListItem title="차단 목록" subtitle="차단한 크리에이터 관리" showChevron />
        </Link>
        <Divider />
        <button type="button" onClick={onLogout} className="block w-full text-left transition-colors hover:bg-surface-container-high">
          <ListItem title="로그아웃" />
        </button>
      </div>
    </div>
  );
}
