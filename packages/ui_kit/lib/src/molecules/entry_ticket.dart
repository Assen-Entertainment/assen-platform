import 'package:core_tokens/core_tokens.dart';
import 'package:flutter/material.dart';
import 'package:ui_kit/src/molecules/ticket_decoration.dart';

/// Queue state of an [AssenEntryTicket].
enum AssenEntryState {
  /// 대기중 — waiting; neutral cream face, number shown.
  waiting,

  /// 호출됨 — called; emphasised strawberry face (the user should come now).
  called,

  /// 입장완료 — entered; muted ink ramp, struck (disabled = muted, tokens.md §1).
  entered,
}

/// A remote-queue entry ticket (`대기중 / 호출됨(강조) / 입장완료`).
///
/// Covers the Domain/EntryTicket row of `components.md` — the @home 앗토엔트리
/// remote line-up pattern. The ticket motif is the tear-off ticket from
/// `tokens.md` §5 (notch + dashed perforation via the shared [TicketPainter],
/// here a horizontal tear with a stub band at the bottom). The three states are
/// distinct in fill and emphasis, never colour alone: [AssenEntryState.called]
/// raises to the strawberry pastel face so a called guest is unmistakable;
/// [AssenEntryState.entered] mutes and strikes the number.
class AssenEntryTicket extends StatelessWidget {
  /// Creates an entry ticket for queue [title] holding [number].
  ///
  /// [state] drives the face/emphasis. [note] is an optional stub line (e.g. an
  /// estimated wait or a venue note).
  const AssenEntryTicket({
    required this.title,
    required this.number,
    this.state = AssenEntryState.waiting,
    this.note,
    super.key,
  });

  /// The queue / venue name (e.g. "하츠코이 본점").
  final String title;

  /// The waiting number (e.g. "A-23").
  final String number;

  /// Queue state — see [AssenEntryState].
  final AssenEntryState state;

  /// Optional stub note (estimated wait, venue line, …).
  final String? note;

  /// Ticket height — a component metric, not a token, so a named constant.
  static const double _height = 168;

  /// The horizontal perforation offset (most of the body, then a stub band).
  static const double _perforation = 124;

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).extension<AssenColors>()!;
    final emphasised = state == AssenEntryState.called;
    final entered = state == AssenEntryState.entered;

    final Color faceFill;
    final Color ink;
    final Color border;
    if (emphasised) {
      faceFill = colors.strawberryBgSubtle;
      ink = colors.strawberryInk;
      border = colors.strawberryBorder;
    } else if (entered) {
      faceFill = colors.cream200;
      ink = colors.ink500;
      border = colors.ink200;
    } else {
      faceFill = colors.cream100;
      ink = colors.ink900;
      border = colors.ink200;
    }

    return SizedBox(
      height: _height,
      child: CustomPaint(
        painter: TicketPainter(
          axis: TicketAxis.horizontal,
          perforation: _perforation,
          fill: faceFill,
          border: border,
          dash: border,
        ),
        child: Column(
          children: [
            SizedBox(
              height: _perforation,
              child: Padding(
                padding: const EdgeInsets.all(SpacingTokens.s4),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Text(
                      title,
                      style: TextStyle(
                        fontSize: TypographyTokens.titleMSize,
                        fontWeight: FontWeight.w600,
                        color: ink,
                      ),
                    ),
                    const SizedBox(height: SpacingTokens.s1),
                    Text(
                      number,
                      style: TextStyle(
                        fontSize: TypographyTokens.displayMSize,
                        fontWeight: FontWeight.w800,
                        color: ink,
                        decoration: entered ? TextDecoration.lineThrough : null,
                      ),
                    ),
                  ],
                ),
              ),
            ),
            Expanded(
              child: Center(
                child: Text(
                  _stateLabel,
                  style: TextStyle(
                    fontSize: TypographyTokens.labelSize,
                    fontWeight: FontWeight.w700,
                    color: emphasised ? colors.roseMain : colors.ink500,
                  ),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  String get _stateLabel => switch (state) {
    AssenEntryState.waiting => note ?? '대기중',
    AssenEntryState.called => '입장해 주세요',
    AssenEntryState.entered => '입장완료',
  };
}
