import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// Provides the placeholder dashboard title.
///
/// P0 wiring proof only; replaced by real operator metrics providers in P5.
/// Declared with the Riverpod 3.x top-level [Provider] API (CONSTRAINTS #40).
final dashboardTitleProvider = Provider<String>((ref) => 'Operator Console');

/// A placeholder operator dashboard screen reading [dashboardTitleProvider].
class PlaceholderDashboardScreen extends ConsumerWidget {
  /// Creates the placeholder dashboard.
  const PlaceholderDashboardScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final title = ref.watch(dashboardTitleProvider);
    return Scaffold(
      body: Center(child: Text(title)),
    );
  }
}
