import 'package:assen_mobile/src/app/router.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:ui_kit/ui_kit.dart';

/// The root widget: a routed [MaterialApp] themed by ui_kit.
///
/// Reads the [routerProvider] and hands the config to [MaterialApp.router]. All
/// colour/typography comes from [AssenTheme]; nothing is styled inline here.
class AssenApp extends ConsumerWidget {
  /// Creates the root app widget.
  const AssenApp({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final router = ref.watch(routerProvider);
    return MaterialApp.router(
      title: 'Assen',
      debugShowCheckedModeBanner: false,
      theme: AssenTheme.light(),
      // The design system is light-first; a dark ramp is deferred (tokens.md
      // §2). Point darkTheme at the light theme and pin ThemeMode.light so the
      // app never shows an unstyled M3 dark scheme. TODO(assen): swap to
      // AssenTheme.dark() once core_tokens ships the dark ramp.
      darkTheme: AssenTheme.light(),
      themeMode: ThemeMode.light,
      routerConfig: router,
    );
  }
}
