import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:operator_features/operator_features.dart';
import 'package:ui_kit/ui_kit.dart';

/// Entry point for the Assen Platform operator app.
///
/// Wraps the tree in a [ProviderScope] (Riverpod 3.x). Routing is absent in P0:
/// go_router is a declared dependency, but the route table is implemented in
/// P3. Until then the app shows a single placeholder dashboard screen.
void main() {
  runApp(const ProviderScope(child: OperatorApp()));
}

/// Root widget of the operator app.
class OperatorApp extends StatelessWidget {
  /// Creates the operator app root.
  const OperatorApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Assen Operator',
      theme: AssenTheme.light(),
      home: const PlaceholderDashboardScreen(),
    );
  }
}
