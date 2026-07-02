"use client";
import * as React from "react";
import { ListItem, Switch, Divider } from "@/components/ui";

/** Settings — 설정. Switch 토글(로컬 상태). */
export default function SettingsPage() {
  const [push, setPush] = React.useState(true);
  const [marketing, setMarketing] = React.useState(false);
  return (
    <div className="mx-auto flex max-w-2xl flex-col gap-4">
      <h1 className="text-headline text-on-surface">설정</h1>
      <div className="overflow-hidden rounded-lg border border-outline">
        <ListItem title="푸시 알림" subtitle="새 포스트·댓글" trailing={<Switch checked={push} onCheckedChange={setPush} />} />
        <Divider />
        <ListItem title="마케팅 수신" subtitle="이벤트·혜택" trailing={<Switch checked={marketing} onCheckedChange={setMarketing} />} />
        <Divider />
        <ListItem title="계정" subtitle="이메일·비밀번호" showChevron />
        <Divider />
        <ListItem title="결제 수단" showChevron />
        <Divider />
        <ListItem title="로그아웃" />
      </div>
    </div>
  );
}
