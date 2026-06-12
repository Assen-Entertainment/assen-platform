import 'package:fan_app/app.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

// Re-export so `package:fan_app/main.dart` keeps exposing [FanApp] (the root
// moved to app.dart in the P3a router migration).
export 'package:fan_app/app.dart' show FanApp;

/// Entry point for the Assen Platform fan app.
///
/// Wraps the tree in a [ProviderScope] (Riverpod 3.x) so the router and auth
/// providers resolve. P3a wires the go_router route table (see
/// `router/fan_router.dart`); the root widget is [FanApp].
void main() {
  runApp(const ProviderScope(child: FanApp()));
}
