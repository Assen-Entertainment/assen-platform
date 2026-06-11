import 'package:core_tokens/core_tokens.dart';
import 'package:flutter/material.dart';

/// Which way a ticket's tear-off perforation runs.
enum TicketAxis {
  /// A vertical perforation carving a right-hand stub (coupon layout).
  vertical,

  /// A horizontal perforation carving a bottom stub (entry-ticket layout).
  horizontal,
}

/// Paints the shared ticket motif: a rounded body with a pair of inward
/// semicircular notches (punch holes) at [perforation] and a dashed
/// perforation line between them.
///
/// Shared by the coupon-ticket-set and entry-ticket molecules (tokens.md §5 —
/// 티켓 절취선: 노치 반경 10 + 점선). It is a package-free [CustomPainter] (the path
/// from `references.md` #8), reused by both ticket molecules rather than
/// re-derived in each. [axis] selects a vertical (coupon) or horizontal (entry)
/// tear; [perforation] is the offset of the notch centres along the cross axis.
///
/// All geometry uses [RadiusTokens] (`ticketNotch`, body `lg`); fill/border/dash
/// colours are passed in from the widget's token lookup, so nothing is
/// hard-coded here.
class TicketPainter extends CustomPainter {
  /// Creates a ticket painter.
  ///
  /// [perforation] is the distance of the notch line from the left edge
  /// ([TicketAxis.vertical]) or the top edge ([TicketAxis.horizontal]).
  /// [fill]/[border]/[dash] come from the design tokens.
  const TicketPainter({
    required this.axis,
    required this.perforation,
    required this.fill,
    required this.border,
    required this.dash,
  });

  /// Tear direction — see [TicketAxis].
  final TicketAxis axis;

  /// Offset of the notch centres / perforation along the cross axis.
  final double perforation;

  /// Body fill colour (token).
  final Color fill;

  /// Body outline colour (token).
  final Color border;

  /// Dash (perforation) colour (token).
  final Color dash;

  static const double _notchRadius = RadiusTokens.ticketNotch;
  static const double _bodyRadius = RadiusTokens.lg;

  @override
  void paint(Canvas canvas, Size size) {
    final isVertical = axis == TicketAxis.vertical;
    final notchA = isVertical ? Offset(perforation, 0) : Offset(0, perforation);
    final notchB = isVertical
        ? Offset(perforation, size.height)
        : Offset(size.width, perforation);

    final path = _ticketPath(size, notchA, notchB);
    canvas
      ..drawPath(path, Paint()..color = fill)
      ..drawPath(
        path,
        Paint()
          ..style = PaintingStyle.stroke
          ..strokeWidth = 1
          ..color = border,
      );

    _drawDashes(canvas, size, isVertical: isVertical);
  }

  void _drawDashes(Canvas canvas, Size size, {required bool isVertical}) {
    final dashPaint = Paint()
      ..color = dash
      ..strokeWidth = 1;
    const dashLen = 4.0;
    const gap = 4.0;
    final extent = isVertical ? size.height : size.width;
    var pos = _notchRadius + dashLen;
    final end = extent - _notchRadius - dashLen;
    while (pos < end) {
      final a = isVertical
          ? Offset(perforation, pos)
          : Offset(pos, perforation);
      final b = isVertical
          ? Offset(perforation, pos + dashLen)
          : Offset(pos + dashLen, perforation);
      canvas.drawLine(a, b, dashPaint);
      pos += dashLen + gap;
    }
  }

  /// The ticket outline: a rounded rect with two notches carved out at
  /// [notchA]/[notchB] on opposite edges.
  Path _ticketPath(Size size, Offset notchA, Offset notchB) {
    final body = Path()
      ..addRRect(
        RRect.fromRectAndRadius(
          Offset.zero & size,
          const Radius.circular(_bodyRadius),
        ),
      );
    final holeA = Path()
      ..addOval(Rect.fromCircle(center: notchA, radius: _notchRadius));
    final holeB = Path()
      ..addOval(Rect.fromCircle(center: notchB, radius: _notchRadius));
    return Path.combine(
      PathOperation.difference,
      Path.combine(PathOperation.difference, body, holeA),
      holeB,
    );
  }

  @override
  bool shouldRepaint(TicketPainter old) =>
      old.axis != axis ||
      old.perforation != perforation ||
      old.fill != fill ||
      old.border != border ||
      old.dash != dash;
}
