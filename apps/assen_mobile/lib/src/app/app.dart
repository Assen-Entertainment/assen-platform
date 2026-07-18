import 'package:assen_mobile/src/app/router.dart';
import 'package:assen_mobile/src/app/theme_mode_controller.dart';
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
      // The fan-chosen mode (밝게/어둡게/시스템 설정), defaulting to
      // `ThemeMode.system` — see `ThemeModeController` (tokens.md §2 dark
      // ramp, ASS-282 design-review follow-up).
      themeMode: ref.watch(themeModeControllerProvider),
      routerConfig: router,
    );
  }
}
