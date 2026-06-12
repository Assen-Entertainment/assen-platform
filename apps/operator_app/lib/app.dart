import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:operator_app/router/operator_router.dart';
import 'package:ui_kit/ui_kit.dart';

/// Root widget of the operator app.
///
/// A [ConsumerWidget] that reads the [operatorRouterProvider] and drives a
/// [MaterialApp.router] under the Assen light theme. Routing is owned by
/// go_router (P3a); the guard redirects on the auth session + role gate (mock
/// today, real opaque-token client + role判定 in P3b — CONSTRAINTS #31).
class OperatorApp extends ConsumerWidget {
  /// Creates the operator app root.
  const OperatorApp({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return MaterialApp.router(
      title: 'Assen Operator',
      debugShowCheckedModeBanner: false,
      theme: AssenTheme.light(),
      routerConfig: ref.watch(operatorRouterProvider),
    );
  }
}
