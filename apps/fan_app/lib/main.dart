import 'package:features/features.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:ui_kit/ui_kit.dart';

/// Entry point for the Assen Platform fan app.
///
/// Wraps the tree in a [ProviderScope] (Riverpod 3.x) so feature providers
/// resolve. Routing is intentionally absent in P0: go_router is declared as a
/// dependency, but the route table is implemented in P3. Until then the app
/// shows a single placeholder feature screen.
void main() {
  runApp(const ProviderScope(child: FanApp()));
}

/// Root widget of the fan app.
class FanApp extends StatelessWidget {
  /// Creates the fan app root.
  const FanApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Assen',
      theme: AssenTheme.light(),
      home: const PlaceholderFeatureScreen(),
    );
  }
}
