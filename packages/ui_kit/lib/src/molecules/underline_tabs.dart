import 'package:core_tokens/core_tokens.dart';
import 'package:flutter/material.dart';

// Typography sizes are literals until TypographyTokens lands.
// TODO(ASS-130): replace with TypographyTokens (tokens.md §3 title.m=16).
const double _tabLabelSize = 16; // tokens.md §3 title.m

/// A horizontally scrollable underline tab strip (`selected / unselected`).
///
/// Covers the Navigation/UnderlineTabs row of `components.md` — the cast and
/// event list filters that can overflow the screen width. Tabs scroll
/// horizontally; the selected tab is inked in `ink.900` with a rose underline
/// indicator, the rest sit in secondary ink. The active state reads from both
/// weight and the underline, not colour alone.
///
/// Touch target: each tab is at least 44pt tall (Korean B2C / HIG).
class AssenUnderlineTabs extends StatelessWidget {
  /// Creates an underline tab strip over [tabs] with [selectedIndex] active.
  ///
  /// [onChanged] reports the tapped index.
  const AssenUnderlineTabs({
    required this.tabs,
    required this.selectedIndex,
    required this.onChanged,
    super.key,
  });

  /// The tab labels, in display order.
  final List<String> tabs;

  /// Index of the currently selected tab.
  final int selectedIndex;

  /// Called with the index of the tapped tab.
  final ValueChanged<int> onChanged;

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).extension<AssenColors>()!;

    return SingleChildScrollView(
      scrollDirection: Axis.horizontal,
      child: Row(
        children: [
          for (var i = 0; i < tabs.length; i++)
            _Tab(
              label: tabs[i],
              selected: i == selectedIndex,
              onTap: () => onChanged(i),
              colors: colors,
            ),
        ],
      ),
    );
  }
}

/// One tab — inked label over a rose underline when selected.
class _Tab extends StatelessWidget {
  const _Tab({
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
        child: Container(
          constraints: const BoxConstraints(minHeight: 44),
          alignment: Alignment.center,
          padding: const EdgeInsets.symmetric(horizontal: SpacingTokens.s4),
          decoration: BoxDecoration(
            border: Border(
              bottom: BorderSide(
                color: selected ? colors.roseMain : Colors.transparent,
                width: 2,
              ),
            ),
          ),
          child: Text(
            label,
            style: TextStyle(
              fontSize: _tabLabelSize,
              fontWeight: selected ? FontWeight.w700 : FontWeight.w500,
              color: selected ? colors.ink900 : colors.ink500,
            ),
          ),
        ),
      ),
    );
  }
}
