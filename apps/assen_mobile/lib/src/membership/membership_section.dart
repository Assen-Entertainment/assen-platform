import 'package:assen_mobile/src/membership/membership_controller.dart';
import 'package:assen_mobile/src/membership/tier.dart';
import 'package:core_tokens/core_tokens.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:ui_kit/ui_kit.dart';

/// The membership block shown on a creator profile: the creator's tiers.
///
/// A [ConsumerWidget] embedded in the creator profile (`creator_screen`), wired
/// to `GET /api/tiers?creator_id=` through [membershipControllerProvider]. It
/// renders nothing while loading skips to a compact skeleton, stays silent when
/// the creator offers no tiers (an empty list is not an error to surface on a
/// profile), shows a compact notice on failure, and otherwise a "멤버십" section
/// of tier cards (the [Tier.featured] one emphasised). Subscribing is a payment
/// gate (IAP) not built on mobile yet, so each tier's 구독 action is shown
/// disabled rather than live.
class MembershipSection extends ConsumerWidget {
  /// Creates the membership section for the creator identified by [creatorId].
  const MembershipSection({required this.creatorId, super.key});

  /// The creator id whose tiers are shown (server `creator_id`).
  final String creatorId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final tiers = ref.watch(membershipControllerProvider(creatorId));
    return tiers.when(
      loading: () => const _MembershipSkeleton(),
      // A tiers fetch failure must not replace the whole profile; keep it
      // compact and inline.
      error: (error, stackTrace) => const Padding(
        padding: EdgeInsets.all(SpacingTokens.s4),
        child: AssenNoticeBar(
          kind: AssenNoticeKind.warning,
          message: '멤버십 정보를 불러오지 못했어요.',
        ),
      ),
      data: (list) =>
          list.isEmpty ? const SizedBox.shrink() : _MembershipList(tiers: list),
    );
  }
}

/// The loaded tiers: a section header over the tier cards.
class _MembershipList extends StatelessWidget {
  const _MembershipList({required this.tiers});

  final List<Tier> tiers;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(
        SpacingTokens.s4,
        SpacingTokens.s6,
        SpacingTokens.s4,
        0,
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          const AssenSectionHeader(title: '멤버십'),
          const SizedBox(height: SpacingTokens.s3),
          for (final tier in tiers) ...[
            _TierCard(tier: tier),
            const SizedBox(height: SpacingTokens.s3),
          ],
        ],
      ),
    );
  }
}

/// One membership tier: name, price/period, benefits, and a disabled 구독 CTA.
class _TierCard extends StatelessWidget {
  const _TierCard({required this.tier});

  final Tier tier;

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).extension<AssenColors>()!;
    return AssenCard(
      level: tier.featured ? AssenCardLevel.level1 : AssenCardLevel.level0,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(
                child: Text(
                  tier.name,
                  style: TextStyle(
                    fontSize: TypographyTokens.titleLSize,
                    fontWeight: FontWeight.w700,
                    color: colors.ink900,
                  ),
                ),
              ),
              if (tier.featured)
                const AssenBadge(label: '추천')
              else if (tier.badge.isNotEmpty)
                AssenBadge(label: tier.badge, hue: AssenBadgeHue.lavender),
            ],
          ),
          const SizedBox(height: SpacingTokens.s2),
          Text(
            tier.pricePeriodLabel,
            style: TextStyle(
              fontSize: TypographyTokens.titleMSize,
              fontWeight: FontWeight.w700,
              color: colors.ink900,
            ),
          ),
          if (tier.benefits.isNotEmpty) ...[
            const SizedBox(height: SpacingTokens.s3),
            for (final benefit in tier.benefits)
              Padding(
                padding: const EdgeInsets.only(bottom: SpacingTokens.s1),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Icon(
                      Icons.check_circle_outline,
                      size: SpacingTokens.s4,
                      color: colors.matchaInk,
                    ),
                    const SizedBox(width: SpacingTokens.s2),
                    Expanded(
                      child: Text(
                        benefit,
                        style: TextStyle(
                          fontSize: TypographyTokens.bodyMSize,
                          height: 1.4,
                          color: colors.ink700,
                        ),
                      ),
                    ),
                  ],
                ),
              ),
          ],
          const SizedBox(height: SpacingTokens.s4),
          // Subscribing is a payment gate (IAP) not built on mobile yet, so the
          // CTA is shown disabled (null onPressed) rather than live.
          const AssenButton(
            label: '구독',
            onPressed: null,
            style: AssenButtonStyle.secondary,
            expand: true,
          ),
        ],
      ),
    );
  }
}

/// The loading state: a compact section-header + card skeleton.
class _MembershipSkeleton extends StatelessWidget {
  const _MembershipSkeleton();

  @override
  Widget build(BuildContext context) {
    return const Padding(
      padding: EdgeInsets.fromLTRB(
        SpacingTokens.s4,
        SpacingTokens.s6,
        SpacingTokens.s4,
        0,
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          AssenSkeleton(width: 120, height: 20),
          SizedBox(height: SpacingTokens.s4),
          AssenSkeleton(width: double.infinity, height: 96, radius: 12),
        ],
      ),
    );
  }
}
