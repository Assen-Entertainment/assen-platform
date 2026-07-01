import { redirect } from "next/navigation";

/** /post (인덱스) → 팔로잉 피드로. 개별 포스트는 /post/[id]. */
export default function PostIndexPage() {
  redirect("/feed");
}
