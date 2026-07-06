import 'package:assen_mobile/src/app/router.dart';
import 'package:assen_mobile/src/common/placeholder_screen.dart';
import 'package:flutter/widgets.dart';
import 'package:go_router/go_router.dart';

/// The creator profile screen, reached via the deep-linkable `/creator/:handle`
/// route (placeholder until the full profile lands — M5).
class CreatorScreen extends StatelessWidget {
  /// Creates the profile screen for the creator identified by [handle].
  const CreatorScreen({required this.handle, super.key});

  /// The @-handle from the route path parameter.
  final String handle;

  @override
  Widget build(BuildContext context) {
    return AssenPlaceholderScreen(
      title: '@$handle',
      message: '크리에이터 프로필은 곧 제공됩니다.',
      // Deep links can open this with no back stack; fall back to the home tab.
      onBack: () =>
          context.canPop() ? context.pop() : context.go(RoutePaths.discovery),
    );
  }
}
