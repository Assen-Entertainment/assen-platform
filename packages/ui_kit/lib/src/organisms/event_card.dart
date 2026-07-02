import 'package:core_tokens/core_tokens.dart';
import 'package:flutter/material.dart';
import 'package:ui_kit/src/atoms/avatar.dart';
import 'package:ui_kit/src/atoms/badges.dart';
import 'package:ui_kit/src/atoms/button.dart';
import 'package:ui_kit/src/atoms/card.dart';

/// Lifecycle of an [AssenEventCard] (`예정/진행중/종료`).
enum AssenEventStatus {
  /// 예정 — upcoming (shows a visit-centric D-day and the booking CTA).
  upcoming,

  /// 진행중 — running now.
  ongoing,

  /// 종료 — finished (muted, no CTA).
  ended,
}

/// An event promo card (`포스터 STRETCH + 기간 + 캐스트`).
///
/// Covers the Domain/EventCard row of `components.md` and the event list/detail
/// (screens.md C4/C5). It composes an [AssenCard] over a full-width poster
/// [slot] (a pastel motif, never a grey box — screens.md 밀도 규칙), a status
/// pill, the run [period], the featured [casts] as overlapping [AssenAvatar]s,
/// and — while bookable — a reservation [AssenButton]. The D-day badge is set
/// by the event run only ("D-5"), never a couple frame (references 금지 #5).
class AssenEventCard extends StatelessWidget {
  /// Creates an event card titled [title].
  ///
  /// [slot] is the poster widget (stretched edge-to-edge at the card top).
  /// [period] is the run window. [status] drives the pill and CTA. [ddayLabel]
  /// is the visit-centric countdown (upcoming only). [casts] are the featured
  /// members. [ctaLabel]/[onCta] add the booking action (hidden when ended).
  const AssenEventCard({
    required this.title,
    required this.period,
    required this.status,
    required this.slot,
    this.ddayLabel,
    this.casts = const [],
    this.ctaLabel,
    this.onCta,
    super.key,
  });

  /// The event title.
  final String title;

  /// The formatted run period (e.g. "6.10 – 6.30").
  final String period;

  /// The event status — see [AssenEventStatus].
  final AssenEventStatus status;

  /// The poster widget, stretched across the card top.
  final Widget slot;

  /// The visit-centric D-day caption (e.g. "D-5"); upcoming only.
  final String? ddayLabel;

  /// The featured cast members (overlapping avatars).
  final List<AssenScheduleCastRef> casts;

  /// Optional booking CTA label (hidden when ended).
  final String? ctaLabel;

  /// The CTA handler.
  final VoidCallback? onCta;

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).extension<AssenColors>()!;
    final isEnded = status == AssenEventStatus.ended;
    final (statusKind, statusLabel) = _status();

    return AssenCard(
      padding: EdgeInsets.zero,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
          // Poster — stretched edge-to-edge, clipped to the card's top radius.
          ClipRRect(
            borderRadius: const BorderRadius.vertical(
              top: Radius.circular(RadiusTokens.lg),
            ),
            child: AspectRatio(aspectRatio: 16 / 9, child: slot),
          ),
          Padding(
            padding: const EdgeInsets.all(SpacingTokens.s4),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                Row(
                  children: [
                    Expanded(
                      child: Text(
                        title,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: TextStyle(
                          fontSize: TypographyTokens.titleMSize,
                          fontWeight: FontWeight.w700,
                          color: colors.ink900,
                        ),
                      ),
                    ),
                    const SizedBox(width: SpacingTokens.s2),
                    AssenStatusBadge(kind: statusKind, label: statusLabel),
                  ],
                ),
                const SizedBox(height: SpacingTokens.s2),
                Row(
                  children: [
                    Icon(
                      Icons.calendar_today_outlined,
                      size: SpacingTokens.s4,
                      color: colors.ink500,
                    ),
                    const SizedBox(width: SpacingTokens.s1),
                    Text(
                      period,
                      style: TextStyle(
                        fontSize: TypographyTokens.bodySSize,
                        fontWeight: FontWeight.w600,
                        color: colors.ink700,
                      ),
                    ),
                    if (ddayLabel != null && !isEnded) ...[
                      const SizedBox(width: SpacingTokens.s2),
                      AssenBadge(label: ddayLabel!, hue: AssenBadgeHue.peach),
                    ],
                  ],
                ),
                if (casts.isNotEmpty) ...[
                  const SizedBox(height: SpacingTokens.s3),
                  _CastStack(casts: casts),
                ],
                if (ctaLabel != null && !isEnded) ...[
                  const SizedBox(height: SpacingTokens.s4),
                  AssenButton(
                    label: ctaLabel!,
                    onPressed: onCta,
                    expand: true,
                  ),
                ],
              ],
            ),
          ),
        ],
      ),
    );
  }

  (AssenStatusKind, String) _status() {
    return switch (status) {
      AssenEventStatus.upcoming => (AssenStatusKind.pending, '예정'),
      AssenEventStatus.ongoing => (AssenStatusKind.confirmed, '진행중'),
      AssenEventStatus.ended => (AssenStatusKind.done, '종료'),
    };
  }
}

/// A featured cast reference for an [AssenEventCard] (name + identity hue).
class AssenScheduleCastRef {
  /// Creates a featured cast reference.
  const AssenScheduleCastRef({required this.name, this.hue});

  /// The cast member's name.
  final String name;

  /// The cast identity hue for the avatar ring (응원색, references #11).
  final AssenBadgeHue? hue;
}

/// Overlapping avatars of the featured cast.
class _CastStack extends StatelessWidget {
  const _CastStack({required this.casts});

  final List<AssenScheduleCastRef> casts;

  @override
  Widget build(BuildContext context) {
    const overlap = 22.0;
    final shown = casts.take(4).toList();
    return SizedBox(
      height: SpacingTokens.s8,
      child: Stack(
        children: [
          for (var i = 0; i < shown.length; i++)
            Positioned(
              left: i * overlap,
              child: AssenAvatar(
                name: shown[i].name,
                hue: shown[i].hue,
                size: AssenAvatarSize.s,
              ),
            ),
        ],
      ),
    );
  }
}
