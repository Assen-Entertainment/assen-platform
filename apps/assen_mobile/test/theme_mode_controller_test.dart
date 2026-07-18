// Unit tests for the theme mode controller (design-review follow-up,
// ASS-282): the default is ThemeMode.system (unchanged app behaviour),
// setThemeMode switches to each fan-selectable mode, a startup load restores
// a previously persisted mode (or falls back to system on a
// missing/unrecognized value), a pick is never clobbered by a still-in-flight
// startup load, and setThemeMode persists the choice for the next launch. No
// widget, no network — the platform channel is stubbed via
// SharedPreferences.setMockInitialValues.

import 'package:assen_mobile/src/app/theme_mode_controller.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

/// The persisted key ThemeModeController reads/writes (kept in sync with the
/// private constant in theme_mode_controller.dart).
const String _prefsKey = 'assen.theme_mode';

/// Lets the controller's async load (or persist) settle.
Future<void> _settle() => Future<void>.delayed(Duration.zero);

void main() {
  setUp(() {
    // A clean, empty store per test unless a test seeds its own values.
    SharedPreferences.setMockInitialValues({});
  });

  test('defaults to ThemeMode.system when nothing is stored', () async {
    final container = ProviderContainer();
    addTearDown(container.dispose);

    expect(container.read(themeModeControllerProvider), ThemeMode.system);
    await _settle();
    expect(container.read(themeModeControllerProvider), ThemeMode.system);
  });

  test('restores a persisted mode on startup', () async {
    SharedPreferences.setMockInitialValues({_prefsKey: 'dark'});
    final container = ProviderContainer();
    addTearDown(container.dispose);
    container.read(themeModeControllerProvider.notifier); // triggers build()
    await _settle();

    expect(container.read(themeModeControllerProvider), ThemeMode.dark);
  });

  test('an unrecognized stored value falls back to system', () async {
    SharedPreferences.setMockInitialValues({_prefsKey: 'not-a-mode'});
    final container = ProviderContainer();
    addTearDown(container.dispose);
    container.read(themeModeControllerProvider.notifier);
    await _settle();

    expect(container.read(themeModeControllerProvider), ThemeMode.system);
  });

  test(
    'a mode picked before the startup load resolves is not clobbered',
    () async {
      // The persisted value is 'dark', but the fan picks 'light' synchronously
      // — before the pending startup _load (kicked off from build()) has a
      // chance to resolve and apply the persisted value.
      SharedPreferences.setMockInitialValues({_prefsKey: 'dark'});
      final container = ProviderContainer();
      addTearDown(container.dispose);

      container
          .read(themeModeControllerProvider.notifier)
          .setThemeMode(ThemeMode.light);
      await _settle();

      expect(container.read(themeModeControllerProvider), ThemeMode.light);
    },
  );

  test('setThemeMode switches to light, dark, then back to system', () async {
    final container = ProviderContainer();
    addTearDown(container.dispose);
    await _settle();

    container
        .read(themeModeControllerProvider.notifier)
        .setThemeMode(
          ThemeMode.light,
        );
    expect(container.read(themeModeControllerProvider), ThemeMode.light);

    container
        .read(themeModeControllerProvider.notifier)
        .setThemeMode(
          ThemeMode.dark,
        );
    expect(container.read(themeModeControllerProvider), ThemeMode.dark);

    container
        .read(themeModeControllerProvider.notifier)
        .setThemeMode(
          ThemeMode.system,
        );
    expect(container.read(themeModeControllerProvider), ThemeMode.system);
  });

  test('setThemeMode persists the choice for the next launch', () async {
    final container = ProviderContainer();
    addTearDown(container.dispose);
    await _settle();

    container
        .read(themeModeControllerProvider.notifier)
        .setThemeMode(ThemeMode.dark);
    await _settle();

    final prefs = await SharedPreferences.getInstance();
    expect(prefs.getString(_prefsKey), 'dark');
  });
}
