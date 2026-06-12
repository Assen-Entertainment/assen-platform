import 'package:flutter/widgets.dart';
import 'package:ui_kit/src/layout/window_size.dart';

/// Centers page content in the Assen expanded-width reading column.
///
/// The wrapper is always a [Center] plus [ConstrainedBox]; below
/// [AssenLayout.contentMaxWidth] it naturally has no visible effect because the
/// parent is already narrower than the maximum. Keeping the same wrapper across
/// widths avoids each screen carrying its own web-specific constraint logic.
class AssenContentColumn extends StatelessWidget {
  /// Creates a centered content column around [child].
  const AssenContentColumn({required this.child, super.key});

  /// The page body constrained to the authored maximum content width.
  final Widget child;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: ConstrainedBox(
        constraints: const BoxConstraints(
          maxWidth: AssenLayout.contentMaxWidth,
        ),
        child: child,
      ),
    );
  }
}
