import 'package:core_tokens/core_tokens.dart';
import 'package:flutter/material.dart';
import 'package:ui_kit/src/atoms/badges.dart';
import 'package:ui_kit/src/atoms/button.dart';
import 'package:ui_kit/src/atoms/card.dart';
import 'package:ui_kit/src/molecules/key_value_row.dart';

// Typography sizes are literals until TypographyTokens lands.
// TODO(ASS-130): replace with TypographyTokens (tokens.md §3).
const double _resTitleSize = 16; // tokens.md §3 title.m — venue title
const double _resDdaySize = 12; // tokens.md §3 body.s — D-day chip

/// State of an [AssenReservationCard] (`다가옴/방문완료/취소`).
enum AssenReservationStatus {
  /// 다가옴 — an upcoming, confirmed booking (shows the D-day + actions).
  upcoming,

  /// 방문완료 — a visited/completed booking.
  visited,

  /// 취소 — a cancelled booking.
  cancelled,
}

/// A reservation summary card (`상태 + 일시 + 인원 + 액션`).
///
/// Covers the Domain/ReservationCard row of `components.md` and the booking
/// screens (screens.md D2/D3). It composes an [AssenCard] with an
/// [AssenStatusBadge] (confirmed/done/cancelled), the date/time and party size
/// as [AssenKeyValueRow]s, and — for upcoming bookings — a D-day chip + action
/// [AssenButton]s (e.g. 변경/취소). The D-day is framed by the visit date only
/// ("D-3", "오늘 방문"), never as a relationship anniversary (references 금지 #5;
/// components.md 관례 #6).
class AssenReservationCard extends StatelessWidget {
  /// Creates a reservation card for the [venue] booking.
  ///
  /// [dateTime] and [partySize] are the formatted detail rows. [status] drives
  /// the badge and which affordances show. [ddayLabel] is the visit-centric
  /// countdown (upcoming only). [primaryLabel]/[onPrimary] and
  /// [secondaryLabel]/[onSecondary] are optional actions (upcoming only).
  const AssenReservationCard({
    required this.venue,
    required this.dateTime,
    required this.partySize,
    required this.status,
    this.ddayLabel,
    this.primaryLabel,
    this.onPrimary,
    this.secondaryLabel,
    this.onSecondary,
    super.key,
  });

  /// The venue/booking title (e.g. "하츠코이 본점").
  final String venue;

  /// The formatted reservation date/time (e.g. "6월 14일 (토) 14:00").
  final String dateTime;

  /// The formatted party size (e.g. "2명").
  final String partySize;

  /// The reservation status — see [AssenReservationStatus].
  final AssenReservationStatus status;

  /// The visit-centric D-day caption (e.g. "D-3"); upcoming bookings only.
  final String? ddayLabel;

  /// Optional primary action label (upcoming only).
  final String? primaryLabel;

  /// The primary action handler.
  final VoidCallback? onPrimary;

  /// Optional secondary action label (upcoming only).
  final String? secondaryLabel;

  /// The secondary action handler.
  final VoidCallback? onSecondary;

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).extension<AssenColors>()!;
    final isUpcoming = status == AssenReservationStatus.upcoming;
    final (statusKind, statusLabel) = _status();

    return AssenCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
          Row(
            children: [
              Expanded(
                child: Text(
                  venue,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: TextStyle(
                    fontSize: _resTitleSize,
                    fontWeight: FontWeight.w700,
                    color: colors.ink900,
                  ),
                ),
              ),
              const SizedBox(width: SpacingTokens.s2),
              AssenStatusBadge(kind: statusKind, label: statusLabel),
            ],
          ),
          if (isUpcoming && ddayLabel != null) ...[
            const SizedBox(height: SpacingTokens.s3),
            _DdayChip(label: ddayLabel!, colors: colors),
          ],
          const SizedBox(height: SpacingTokens.s3),
          AssenKeyValueRow(label: '일시', value: dateTime),
          const SizedBox(height: SpacingTokens.s2),
          AssenKeyValueRow(label: '인원', value: partySize),
          if (isUpcoming &&
              (primaryLabel != null || secondaryLabel != null)) ...[
            const SizedBox(height: SpacingTokens.s4),
            Row(
              children: [
                if (secondaryLabel != null)
                  Expanded(
                    child: AssenButton(
                      label: secondaryLabel!,
                      style: AssenButtonStyle.ghost,
                      onPressed: onSecondary,
                      expand: true,
                    ),
                  ),
                if (secondaryLabel != null && primaryLabel != null)
                  const SizedBox(width: SpacingTokens.s3),
                if (primaryLabel != null)
                  Expanded(
                    child: AssenButton(
                      label: primaryLabel!,
                      style: AssenButtonStyle.secondary,
                      onPressed: onPrimary,
                      expand: true,
                    ),
                  ),
              ],
            ),
          ],
        ],
      ),
    );
  }

  (AssenStatusKind, String) _status() {
    return switch (status) {
      AssenReservationStatus.upcoming => (AssenStatusKind.confirmed, '예약 확정'),
      AssenReservationStatus.visited => (AssenStatusKind.done, '방문 완료'),
      AssenReservationStatus.cancelled => (AssenStatusKind.cancelled, '취소됨'),
    };
  }
}

/// The visit-centric D-day chip (strawberry surface, hue ink).
class _DdayChip extends StatelessWidget {
  const _DdayChip({required this.label, required this.colors});

  final String label;
  final AssenColors colors;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(
        horizontal: SpacingTokens.s2,
        vertical: SpacingTokens.s1,
      ),
      decoration: BoxDecoration(
        color: colors.strawberryBg,
        borderRadius: const BorderRadius.all(Radius.circular(RadiusTokens.sm)),
        border: Border.all(color: colors.strawberryBorder),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(
            Icons.event_available_outlined,
            size: SpacingTokens.s4,
            color: colors.strawberryInk,
          ),
          const SizedBox(width: SpacingTokens.s1),
          Text(
            label,
            style: TextStyle(
              fontSize: _resDdaySize,
              fontWeight: FontWeight.w700,
              color: colors.strawberryInk,
            ),
          ),
        ],
      ),
    );
  }
}
