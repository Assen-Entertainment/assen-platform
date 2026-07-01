import { MembershipTierCard } from "@/components/ui";
import { getMembershipTiers } from "@/lib/api";

/** Membership — 멤버십 티어 둘러보기. 서버 fetch(tiers). */
export default async function MembershipPage() {
  const tiers = await getMembershipTiers();
  return (
    <div className="mx-auto flex max-w-5xl flex-col gap-6">
      <h1 className="text-headline text-on-surface">멤버십</h1>
      <p className="text-body-m text-on-surface-variant">크리에이터를 정기 후원하고 전용 혜택을 받아보세요.</p>
      <div className="grid gap-4 sm:grid-cols-3">
        {tiers.map((t) => (
          <MembershipTierCard
            key={t.id}
            name={t.name}
            price={t.price}
            period={t.period}
            benefits={t.benefits}
            badge={t.badge}
            featured={t.featured}
          />
        ))}
      </div>
    </div>
  );
}
