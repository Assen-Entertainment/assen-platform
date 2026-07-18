"use client";
import { ListItem, Switch, Divider, SectionHeader, Spinner } from "@/components/ui";
import { usePersistentToggle } from "@/lib/use-persistent-state";
import { useMarketingConsent, useSetMarketingConsent } from "@/lib/api/queries";
import type { MarketingConsentState } from "@/lib/api/types";

/** 알림 카테고리 정의 — 키는 localStorage 영속 식별자. */
const CATEGORIES: { key: string; title: string; subtitle: string; defaultOn: boolean }[] = [
  { key: "assen.notif.newPost", title: "새 포스트", subtitle: "구독한 크리에이터의 새 글", defaultOn: true },
  { key: "assen.notif.comment", title: "댓글·답글", subtitle: "내 글/댓글에 달린 반응", defaultOn: true },
  { key: "assen.notif.like", title: "좋아요", subtitle: "내 포스트에 눌린 좋아요", defaultOn: false },
  { key: "assen.notif.membership", title: "멤버십·구독", subtitle: "구독 갱신·혜택 안내", defaultOn: true },
  { key: "assen.notif.order", title: "주문·배송", subtitle: "결제·배송 상태 변경", defaultOn: true },
  // ※마케팅·이벤트는 아래 MarketingConsentSection(서버 저장)이 단일 진실원천 — 로컬 토글로 중복하지 않는다(#7/#8).
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

      <MarketingConsentSection />
    </div>
  );
}

/** 마케팅 수신 동의(D8) — 채널별 서버 저장(GET/PUT /fan/marketing). 선택 동의. */
function MarketingConsentSection() {
  const { data, isLoading } = useMarketingConsent();
  const save = useSetMarketingConsent();
  const state: MarketingConsentState = data ?? { push: false, sms: false, email: false };

  const setChannel = (channel: keyof MarketingConsentState, on: boolean) => {
    save.mutate({ ...state, [channel]: on });
  };

  return (
    <div className="flex flex-col gap-2">
      <SectionHeader
        title="마케팅 수신 동의"
        description="이벤트·혜택 소식을 받을 채널을 선택하세요 (선택 · 언제든 해제 가능)"
      />
      <div className="overflow-hidden rounded-lg border border-outline">
        {isLoading ? (
          <div className="flex justify-center py-8">
            <Spinner />
          </div>
        ) : (
          <>
            <ListItem
              title="앱 푸시 알림"
              subtitle="혜택·이벤트 푸시"
              trailing={
                <Switch
                  aria-label="앱 푸시 마케팅 수신"
                  checked={state.push}
                  onCheckedChange={(v) => setChannel("push", v)}
                  disabled={save.isPending}
                />
              }
            />
            <Divider />
            <ListItem
              title="문자(SMS)"
              subtitle="프로모션 문자"
              trailing={
                <Switch
                  aria-label="SMS 마케팅 수신"
                  checked={state.sms}
                  onCheckedChange={(v) => setChannel("sms", v)}
                  disabled={save.isPending}
                />
              }
            />
            <Divider />
            <ListItem
              title="이메일"
              subtitle="이메일은 현재 수집하지 않아요"
              trailing={
                <Switch aria-label="이메일 마케팅 수신" checked={state.email} disabled />
              }
            />
          </>
        )}
      </div>
      <p className="text-caption text-on-surface-variant">
        동의하지 않아도 서비스 이용에는 제한이 없어요.
      </p>
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
