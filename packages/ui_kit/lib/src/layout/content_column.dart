import 'package:flutter/widgets.dart';
import 'package:ui_kit/src/layout/window_size.dart';

/// Centers page content in an Assen expanded-width content column.
///
/// The wrapper is always a [Center] plus [ConstrainedBox]; below [maxWidth] it
/// naturally has no visible effect because the parent is already narrower than
/// the maximum. Keeping the same wrapper across widths avoids each screen
/// carrying its own web-specific constraint logic. [maxWidth] defaults to the
/// fan reading column ([AssenLayout.contentMaxWidth]); the operator console
/// passes the wider [AssenLayout.consoleContentMaxWidth].
class AssenContentColumn extends StatelessWidget {
  /// Creates a centered content column around [child].
  const AssenContentColumn({
    required this.child,
    this.maxWidth = AssenLayout.contentMaxWidth,
    super.key,
  });

  /// The page body constrained to [maxWidth].
  final Widget child;

  /// The maximum content width before the column centers in available space.
  final double maxWidth;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: ConstrainedBox(
        constraints: BoxConstraints(maxWidth: maxWidth),
        child: child,
      ),
    );
  }
}
