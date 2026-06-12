import 'package:fan_app/router/fan_router.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:ui_kit/ui_kit.dart';

/// Root widget of the fan app.
///
/// A [ConsumerWidget] that reads the [fanRouterProvider] and drives a
/// [MaterialApp.router] under the Assen light theme. Routing is owned by
/// go_router (P3a); the guard redirects on the auth session (mock today, real
/// opaque-token client in P3b — CONSTRAINTS #31).
class FanApp extends ConsumerWidget {
  /// Creates the fan app root.
  const FanApp({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return MaterialApp.router(
      title: 'Assen',
      debugShowCheckedModeBanner: false,
      theme: AssenTheme.light(),
      routerConfig: ref.watch(fanRouterProvider),
    );
  }
}
