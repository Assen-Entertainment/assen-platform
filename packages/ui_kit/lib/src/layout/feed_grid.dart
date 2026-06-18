import 'package:core_tokens/core_tokens.dart';
import 'package:flutter/widgets.dart';

/// A responsive grid feed of heterogeneous cards, laid out row-major.
///
/// Children fill left-to-right, top-to-bottom across up to [maxColumns]. The
/// column count derives from this widget's OWN `constraints.maxWidth` (the
/// local pane width, never the window width — a desktop sidebar shrinks the
/// body below the window, so window-width math would over-count columns).
///
/// Because the tree is built as actual rows (a [Column] of [Row]s), the
/// source / screen-reader / focus order matches the visual reading order; the
/// first two children always share the first row when there are ≥2 columns. A
/// partial final row keeps each card at its column width via empty flex cells
/// rather than stretching it across the row.
///
/// Each cell is independently sized (no fixed `childAspectRatio`), so cards of
/// different intrinsic heights lay out without stretching or clipping; rows are
/// top-aligned (grid-like, not height-balanced masonry). At one column it
/// degrades to a single stacked column.
class AssenFeedGrid extends StatelessWidget {
  /// Creates a responsive feed of [children].
  const AssenFeedGrid({
    required this.children,
    this.minColumnWidth = 360,
    this.maxColumns = 3,
    this.columnSpacing = SpacingTokens.s5,
    this.rowSpacing = SpacingTokens.s6,
    super.key,
  }) : assert(maxColumns >= 1, 'maxColumns must be >= 1');

  /// The feed cards, laid out in row-major order across the columns.
  final List<Widget> children;

  /// The smallest a column may get before the count drops by one.
  final double minColumnWidth;

  /// The upper bound on columns regardless of how wide the pane gets.
  final int maxColumns;

  /// Horizontal gap between columns.
  final double columnSpacing;

  /// Vertical gap between cards stacked within a column.
  final double rowSpacing;

  /// The resolved column count for a given local pane [width].
  ///
  /// Exposed so geometry tests can assert the count derives from the pane width
  /// rather than the window width.
  int columnsForWidth(double width) {
    if (!width.isFinite || width <= 0) return 1;
    final raw = ((width + columnSpacing) / (minColumnWidth + columnSpacing))
        .floor();
    return raw.clamp(1, maxColumns);
  }

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (context, constraints) {
        final columns = columnsForWidth(constraints.maxWidth);
        if (columns <= 1 || children.length <= 1) {
          return Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: _withRowSpacing(children),
          );
        }

        // Chunk row-major into rows of [columns] so the WIDGET TREE order
        // matches the visual (and screen-reader / focus) reading order. A
        // partial final row keeps each card at its column width via empty flex
        // cells rather than stretching it across the row.
        final rows = <Widget>[];
        for (var start = 0; start < children.length; start += columns) {
          final cells = <Widget>[];
          for (var c = 0; c < columns; c++) {
            if (c > 0) cells.add(SizedBox(width: columnSpacing));
            final index = start + c;
            cells.add(
              Expanded(
                child: index < children.length
                    ? children[index]
                    : const SizedBox.shrink(),
              ),
            );
          }
          rows.add(
            Row(crossAxisAlignment: CrossAxisAlignment.start, children: cells),
          );
        }

        return Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: _withRowSpacing(rows),
        );
      },
    );
  }

  List<Widget> _withRowSpacing(List<Widget> items) => [
    for (var i = 0; i < items.length; i++) ...[
      if (i > 0) SizedBox(height: rowSpacing),
      items[i],
    ],
  ];
}
