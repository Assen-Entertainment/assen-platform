import { redirect } from "next/navigation";

/** /creator → 기본 크리에이터로. (동적 라우트 /creator/[handle] 사용) */
export default function CreatorIndex() {
  redirect("/creator/stellar");
}
