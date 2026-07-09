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
      darkTheme: AssenTheme.dark(),
      // `themeMode` is left unset — `ThemeMode.system` is MaterialApp's own
      // default, so the app follows the OS/device theme setting (tokens.md
      // §2 dark ramp, ASS-282) without an explicit (lint-redundant) value.
      routerConfig: router,
    );
  }
}
