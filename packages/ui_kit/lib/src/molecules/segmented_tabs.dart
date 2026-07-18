import 'package:core_tokens/core_tokens.dart';
import 'package:flutter/material.dart';

/// A segmented control for switching between a small set of views
/// (`selected / unselected`).
///
/// Covers the Navigation/SegmentedTabs row of `components.md` — the operator
/// screen's 2-way (or few-way) view switch. The whole control is an inset track
/// (cream fill) and the selected segment is a raised white pill so the active
/// view reads clearly without relying on hue alone. Labels are the only
/// content; the index is fully controlled by the caller.
///
/// Touch target: each segment is at least 44pt tall (Korean B2C / HIG).
class AssenSegmentedTabs extends StatelessWidget {
  /// Creates a segmented control over [segments] with [selectedIndex] active.
  ///
  /// [onChanged] reports the tapped index. There must be at least two segments
  /// (a single-segment control is meaningless).
  const AssenSegmentedTabs({
    required this.segments,
    required this.selectedIndex,
    required this.onChanged,
    super.key,
  }) : assert(segments.length >= 2, 'A segmented control needs 2+ segments');

  /// The segment labels, in display order.
  final List<String> segments;

  /// Index of the currently selected segment.
  final int selectedIndex;

  /// Called with the index of the tapped segment.
  final ValueChanged<int> onChanged;

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).extension<AssenColors>()!;

    return Container(
      padding: const EdgeInsets.all(SpacingTokens.s1),
      decoration: BoxDecoration(
        color: colors.neutral200,
        borderRadius: const BorderRadius.all(Radius.circular(RadiusTokens.md)),
      ),
      child: Row(
        children: [
          for (var i = 0; i < segments.length; i++)
            Expanded(
              child: _Segment(
                label: segments[i],
                selected: i == selectedIndex,
                onTap: () => onChanged(i),
                colors: colors,
              ),
            ),
        ],
      ),
    );
  }
}

/// One segment pill — white and raised when selected, transparent otherwise.
class _Segment extends StatelessWidget {
  const _Segment({
    required this.label,
    required this.selected,
    required this.onTap,
    required this.colors,
  });

  final String label;
  final bool selected;
  final VoidCallback onTap;
  final AssenColors colors;

  @override
  Widget build(BuildContext context) {
    return Semantics(
      button: true,
      selected: selected,
      child: GestureDetector(
        onTap: onTap,
        behavior: HitTestBehavior.opaque,
        child: AnimatedContainer(
          duration: MotionDurations.short,
          constraints: const BoxConstraints(minHeight: 44 - SpacingTokens.s2),
          alignment: Alignment.center,
          decoration: BoxDecoration(
            color: selected ? colors.white : Colors.transparent,
            borderRadius: const BorderRadius.all(
              Radius.circular(RadiusTokens.sm),
            ),
            boxShadow: selected
                ? const [
                    BoxShadow(
                      color: ElevationTokens.level1Color,
                      offset: Offset(
                        ElevationTokens.level1OffsetX,
                        ElevationTokens.level1OffsetY,
                      ),
                      blurRadius: ElevationTokens.level1Blur,
                    ),
                  ]
                : null,
          ),
          child: Text(
            label,
            style: TextStyle(
              fontSize: TypographyTokens.labelSize,
              fontWeight: selected ? FontWeight.w700 : FontWeight.w500,
              color: selected ? colors.ink900 : colors.ink600,
            ),
          ),
        ),
      ),
    );
  }
}
