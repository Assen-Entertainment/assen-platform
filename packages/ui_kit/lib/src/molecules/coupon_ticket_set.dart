import 'package:core_tokens/core_tokens.dart';
import 'package:flutter/material.dart';
import 'package:ui_kit/src/molecules/ticket_decoration.dart';

// Typography sizes are literals until TypographyTokens lands.
// TODO(ASS-130): replace with TypographyTokens (tokens.md §3 title.l/body.s).
const double _couponTitleSize = 19; // tokens.md §3 title.l — coupon headline
const double _couponMetaSize = 12; // tokens.md §3 body.s — validity / terms
const double _couponStubSize = 13; // tokens.md §3 label — tear-off stub

/// Redemption state of an [AssenCouponTicketSet].
enum AssenCouponState {
  /// 사용가능 — redeemable; full-colour strawberry face with a live stub.
  available,

  /// 사용완료 — already redeemed; muted ink ramp with a struck label
  /// (disabled = muted, never darker — tokens.md §1).
  used,
}

/// A perforated coupon ticket (`사용가능 / 사용완료`).
///
/// Covers the Domain/CouponTicket row of `components.md`, replacing the
/// deprecated single `CouponTicket` with the set/ticket form. The motif is the
/// tear-off ticket from `tokens.md` §5 — a notched body with a dashed
/// perforation separating the main coupon from the redeem stub (drawn by the
/// shared [TicketPainter], the package-free path from `references.md` #8). The
/// available face uses the strawberry pastel (fill-only — text is strawberry
/// ink); the used face mutes to the ink ramp.
class AssenCouponTicketSet extends StatelessWidget {
  /// Creates a coupon titled [title].
  ///
  /// [subtitle] is supporting copy (e.g. the offer detail); [validity] is the
  /// expiry line (visit-/validity-centric framing, references #12). [stubLabel]
  /// is the tear-off action text. [onRedeem] fires when an available coupon's
  /// stub is tapped (ignored when [state] is used).
  const AssenCouponTicketSet({
    required this.title,
    required this.validity,
    this.subtitle,
    this.stubLabel = '사용하기',
    this.state = AssenCouponState.available,
    this.onRedeem,
    super.key,
  });

  /// The coupon headline (e.g. "디저트 1+1").
  final String title;

  /// The validity line (e.g. "~2026.07.31 까지").
  final String validity;

  /// Optional supporting copy under the title.
  final String? subtitle;

  /// The tear-off stub label.
  final String stubLabel;

  /// Redemption state — see [AssenCouponState].
  final AssenCouponState state;

  /// Called when an available coupon's stub is tapped.
  final VoidCallback? onRedeem;

  bool get _used => state == AssenCouponState.used;

  /// Where the perforation sits — most of the height is the main coupon, the
  /// remainder is the stub. A component metric (not a token), so it is a named
  /// constant.
  static const double _height = 132;
  static const double _stubWidth = 92;

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).extension<AssenColors>()!;
    final faceFill = _used ? colors.cream200 : colors.strawberryBgSubtle;
    final ink = _used ? colors.ink500 : colors.strawberryInk;
    final border = _used ? colors.ink200 : colors.strawberryBorder;

    return SizedBox(
      height: _height,
      child: LayoutBuilder(
        builder: (context, constraints) {
          // The tear-off stub is carved from the right edge, so the perforation
          // runs vertically at the stub boundary (shared TicketPainter).
          final stubLeft = constraints.maxWidth - _stubWidth;
          return CustomPaint(
            painter: TicketPainter(
              axis: TicketAxis.vertical,
              perforation: stubLeft,
              fill: faceFill,
              border: border,
              dash: border,
            ),
            child: Row(
              children: [
                Expanded(
                  child: Padding(
                    padding: const EdgeInsets.all(SpacingTokens.s4),
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          title,
                          style: TextStyle(
                            fontSize: _couponTitleSize,
                            fontWeight: FontWeight.w700,
                            color: ink,
                            decoration: _used
                                ? TextDecoration.lineThrough
                                : null,
                          ),
                        ),
                        if (subtitle != null) ...[
                          const SizedBox(height: SpacingTokens.s1),
                          Text(
                            subtitle!,
                            style: TextStyle(
                              fontSize: _couponMetaSize,
                              color: ink,
                            ),
                          ),
                        ],
                        const SizedBox(height: SpacingTokens.s2),
                        Text(
                          validity,
                          style: TextStyle(
                            fontSize: _couponMetaSize,
                            color: colors.ink500,
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
                SizedBox(
                  width: _stubWidth,
                  child: _Stub(
                    label: _used ? '사용완료' : stubLabel,
                    used: _used,
                    ink: ink,
                    onTap: _used ? null : onRedeem,
                  ),
                ),
              ],
            ),
          );
        },
      ),
    );
  }
}

/// The tear-off stub — a tappable redeem action when available.
class _Stub extends StatelessWidget {
  const _Stub({
    required this.label,
    required this.used,
    required this.ink,
    required this.onTap,
  });

  final String label;
  final bool used;
  final Color ink;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    final content = Center(
      child: Text(
        label,
        textAlign: TextAlign.center,
        style: TextStyle(
          fontSize: _couponStubSize,
          fontWeight: FontWeight.w700,
          color: ink,
        ),
      ),
    );
    if (onTap == null) return content;
    return GestureDetector(
      onTap: onTap,
      behavior: HitTestBehavior.opaque,
      child: content,
    );
  }
}
