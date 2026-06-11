import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// Provides the placeholder feature's greeting string.
///
/// Exists only to prove the Riverpod 3.x wiring compiles in P0. Real feature
/// providers replace it from P3. Declared with the 3.x top-level [Provider]
/// API (CONSTRAINTS #40).
final greetingProvider = Provider<String>((ref) => 'Assen Platform');

/// A placeholder feature screen reading [greetingProvider].
///
/// Demonstrates the app -> features -> Riverpod path end to end without
/// committing to any P0 product surface.
class PlaceholderFeatureScreen extends ConsumerWidget {
  /// Creates the placeholder screen.
  const PlaceholderFeatureScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final greeting = ref.watch(greetingProvider);
    return Scaffold(
      body: Center(child: Text(greeting)),
    );
  }
}
