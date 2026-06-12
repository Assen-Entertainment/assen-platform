import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:operator_app/app.dart';

// Re-export so `package:operator_app/main.dart` keeps exposing [OperatorApp]
// (the root moved to app.dart in the P3a router migration).
export 'package:operator_app/app.dart' show OperatorApp;

/// Entry point for the Assen Platform operator app.
///
/// Wraps the tree in a [ProviderScope] (Riverpod 3.x) so the router and auth
/// providers resolve. P3a wires the go_router route table (see
/// `router/operator_router.dart`); the root widget is [OperatorApp].
void main() {
  runApp(const ProviderScope(child: OperatorApp()));
}
