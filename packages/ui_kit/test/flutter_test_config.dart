// Package-wide test bootstrap (Flutter auto-loads `flutter_test_config.dart`).
//
// Alchemist golden tests (`goldenTest(...)`) render each scenario's `child`
// through Alchemist's own harness, NOT the `MaterialApp(theme: AssenTheme…)`
// wrapper the plain `testWidgets` cases use. With no theme configured,
// Alchemist falls back to `ThemeData.fallback()`, which carries none of Assen's
// `ThemeExtension`s — so every atom/molecule/organism that reads
// `Theme.of(context).extension<AssenColors>()!` crashes with a null-check error
// during build (surfaced only when the #31 goldens are un-skipped and generated
// on CI). Registering the Assen light theme as Alchemist's global config theme
// makes `extension<AssenColors>()` resolve for all golden scenarios at once —
// the resolution order is variant theme → inherited theme → this global theme →
// fallback (see alchemist `_resolveThemeOf`).
//
// This only affects Alchemist golden tests; plain `testWidgets` ignore the
// AlchemistConfig zone value and keep using their own `_host` theme wrapper.

import 'dart:async';

import 'package:alchemist/alchemist.dart';
import 'package:ui_kit/ui_kit.dart';

Future<void> testExecutable(FutureOr<void> Function() testMain) async {
  return AlchemistConfig.runWithConfig(
    config: AlchemistConfig(theme: AssenTheme.light()),
    run: testMain,
  );
}
