import 'package:core_tokens/core_tokens.dart';
import 'package:flutter/widgets.dart';
import 'package:ui_kit/src/layout/window_size.dart';

/// Material 3 "list-detail" canonical layout for the fan web desktop IA.
///
/// At [breakpoint] and wider it lays a [list] pane beside a [detail] pane (side
/// by side, the detail pane taking the flexible remaining width); below the
/// breakpoint it renders ONLY the [list] and the caller drives navigation to a
/// full detail route (push). This keeps the mobile single-column flow unchanged
/// while a desktop browser fills the surface with both panes.
///
/// Widths are read from the LOCAL `constraints.maxWidth`, so it composes
/// correctly inside a desktop sidebar shell (the body, not the window, decides
/// the split). The list pane is either a fixed [listPaneWidth] (e.g. a 360dp
/// menu/master column) or, when that is null, a flexible pane sized by
/// [listFlex] against the detail pane's [detailFlex].
///
/// Selection state is the CALLER's concern — this is a pure layout. The caller
/// passes the already-selected item's body as [detail] (or a placeholder widget
/// when nothing is selected) and rebuilds when the selection changes. For
/// out-of-shell routes the caller should hold the selection in screen-local /
/// auto-disposing state (never an app-global provider), so leaving and
/// re-entering the route resets the detail pane.
class AssenListDetailScaffold extends StatelessWidget {
  /// Creates a list-detail layout.
  const AssenListDetailScaffold({
    required this.list,
    required this.detail,
    this.breakpoint = AssenWindowSize.large,
    this.listPaneWidth,
    this.listFlex = 3,
    this.detailFlex = 2,
    this.gap = SpacingTokens.s6,
    super.key,
  }) : assert(listFlex > 0, 'listFlex must be > 0'),
       assert(detailFlex > 0, 'detailFlex must be > 0');

  /// The list/master pane (left). Rendered alone below [breakpoint].
  final Widget list;

  /// The detail pane (right) shown beside [list] at [breakpoint] and wider.
  final Widget detail;

  /// The smallest size class at which the two panes sit side by side.
  ///
  /// Defaults to [AssenWindowSize.large] (1200dp): a list-detail shows two full
  /// content panes, so it needs more room than a supporting-pane rail, and the
  /// out-of-shell detail surfaces it serves render against the full window.
  final AssenWindowSize breakpoint;

  /// Fixed width of the list pane when side-by-side; when null the list pane is
  /// flexible (sized by [listFlex] against [detailFlex]).
  final double? listPaneWidth;

  /// Flex weight of the list pane when [listPaneWidth] is null.
  final int listFlex;

  /// Flex weight of the detail pane when side-by-side.
  final int detailFlex;

  /// Gap between the two panes.
  final double gap;

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (context, constraints) {
        final size = AssenWindowSize.fromWidth(constraints.maxWidth);
        if (!size.atLeast(breakpoint)) return list;

        final listPane = listPaneWidth != null
            ? SizedBox(width: listPaneWidth, child: list)
            : Expanded(flex: listFlex, child: list);

        return Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            listPane,
            SizedBox(width: gap),
            Expanded(flex: detailFlex, child: detail),
          ],
        );
      },
    );
  }
}
