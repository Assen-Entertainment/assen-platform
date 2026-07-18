import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { getCreator, getCreators } from "@/lib/api";
import { FollowersView } from "./followers-view";

/** 팔로워/팔로잉 목록 — /creator/[handle]/followers. mock(다른 크리에이터로 목록 구성). */
export default async function FollowersPage({ params }: { params: Promise<{ handle: string }> }) {
  const { handle } = await params;
  const creator = await getCreator(handle);
  if (!creator) notFound();
  const all = await getCreators();
  const others = all.filter((c) => c.handle !== handle);
  return <FollowersView creatorName={creator.name} followers={others} following={others.slice(0, 2)} />;
}

export async function generateMetadata({ params }: { params: Promise<{ handle: string }> }): Promise<Metadata> {
  const { handle } = await params;
  const creator = await getCreator(handle);
  return { title: creator ? `${creator.name}의 팔로워` : "팔로워" };
}
