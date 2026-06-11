import 'package:core_tokens/core_tokens.dart';
import 'package:flutter/material.dart';

/// A selectable filter chip (`selected / unselected`, optional count).
///
/// Covers the Inputs/FilterChip row of `components.md` — collection filters and
/// the 출근표 (schedule) date picker, and is reused for PartySizeChip via the
/// [label]. Selected uses a strawberry pastel fill with strawberry ink text
/// (pastels are surface-only; text is the hue's ink — tokens.md §1); unselected
/// is an outlined cream surface. No gradients — solid fills only.
class AssenFilterChip extends StatelessWidget {
  /// Creates a filter chip labelled [label].
  ///
  /// [selected] drives the active styling. [onSelected] receives the toggled
  /// value; null disables the chip. [count] optionally appends a tally
  /// (e.g. "체키 12").
  const AssenFilterChip({
    required this.label,
    required this.selected,
    required this.onSelected,
    this.count,
    super.key,
  });

  /// The chip text.
  final String label;

  /// Whether the chip is currently selected.
  final bool selected;

  /// Called with the toggled selection value. Null disables the chip.
  final ValueChanged<bool>? onSelected;

  /// Optional trailing count shown after [label].
  final int? count;

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).extension<AssenColors>()!;
    final enabled = onSelected != null;
    final fg = !enabled
        ? colors.ink500
        : (selected ? colors.strawberryInk : colors.ink700);

    return Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: enabled ? () => onSelected!(!selected) : null,
        borderRadius: const BorderRadius.all(
          Radius.circular(RadiusTokens.full),
        ),
        child: Container(
          constraints: const BoxConstraints(minHeight: 36),
          padding: const EdgeInsets.symmetric(
            horizontal: SpacingTokens.s4,
            vertical: SpacingTokens.s2,
          ),
          decoration: BoxDecoration(
            color: selected ? colors.strawberryBg : colors.cream50,
            borderRadius: const BorderRadius.all(
              Radius.circular(RadiusTokens.full),
            ),
            border: Border.all(
              color: selected ? colors.strawberryBorder : colors.ink200,
            ),
          ),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(
                label,
                style: TextStyle(
                  color: fg,
                  fontSize: 13,
                  fontWeight: selected ? FontWeight.w600 : FontWeight.w500,
                ),
              ),
              if (count != null) ...[
                const SizedBox(width: SpacingTokens.s1),
                Text(
                  '$count',
                  style: TextStyle(
                    color: fg,
                    fontSize: 13,
                    fontWeight: FontWeight.w700,
                  ),
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }
}

/// Availability of a [AssenTimeSlotChip].
enum AssenTimeSlotState {
  /// Bookable — tappable, outlined surface.
  available,

  /// Fully booked — struck through and non-interactive (the time is shown but
  /// clearly closed, a common Korean reservation pattern).
  full,

  /// Chosen by the user — solid action-anchor fill.
  selected,
}

/// A reservation time-slot chip (`available / full / selected`).
///
/// Covers the Domain/TimeSlotChip row of `components.md`. The three states are
/// distinct in more than colour: [AssenTimeSlotState.full] adds a strikethrough
/// so a closed slot is unmistakable, and [AssenTimeSlotState.selected] fills
/// with the solid rose anchor. Tap is ignored unless the slot is available.
class AssenTimeSlotChip extends StatelessWidget {
  /// Creates a time-slot chip showing [label] (e.g. "14:30") in [state].
  ///
  /// [onTap] fires only when [state] is [AssenTimeSlotState.available].
  const AssenTimeSlotChip({
    required this.label,
    required this.state,
    required this.onTap,
    super.key,
  });

  /// The slot label, typically a time (e.g. "14:30").
  final String label;

  /// The slot's availability — drives styling and interactivity.
  final AssenTimeSlotState state;

  /// Tap handler, honoured only for available slots.
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).extension<AssenColors>()!;
    final isAvailable = state == AssenTimeSlotState.available;
    final isSelected = state == AssenTimeSlotState.selected;
    final isFull = state == AssenTimeSlotState.full;

    final Color background;
    final Color border;
    final Color text;
    if (isSelected) {
      background = colors.roseMain;
      border = colors.roseMain;
      text = colors.white;
    } else if (isFull) {
      background = colors.ink100;
      border = colors.ink200;
      text = colors.ink500;
    } else {
      background = colors.cream50;
      border = colors.ink200;
      text = colors.ink900;
    }

    return Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: isAvailable ? onTap : null,
        borderRadius: const BorderRadius.all(Radius.circular(RadiusTokens.sm)),
        child: Container(
          constraints: const BoxConstraints(minHeight: 44, minWidth: 64),
          alignment: Alignment.center,
          padding: const EdgeInsets.symmetric(
            horizontal: SpacingTokens.s3,
            vertical: SpacingTokens.s2,
          ),
          decoration: BoxDecoration(
            color: background,
            borderRadius: const BorderRadius.all(
              Radius.circular(RadiusTokens.sm),
            ),
            border: Border.all(color: border),
          ),
          child: Text(
            label,
            style: TextStyle(
              color: text,
              fontSize: 14,
              fontWeight: isSelected ? FontWeight.w700 : FontWeight.w500,
              decoration: isFull ? TextDecoration.lineThrough : null,
              decorationColor: colors.ink500,
            ),
          ),
        ),
      ),
    );
  }
}
