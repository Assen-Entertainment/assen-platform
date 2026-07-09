// Unit tests for the theme mode controller (design-review follow-up,
// ASS-282): the default is ThemeMode.system (unchanged app behaviour), and
// setThemeMode switches to each fan-selectable mode. No widget, no network.

import 'package:assen_mobile/src/app/theme_mode_controller.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  test('defaults to ThemeMode.system', () {
    final container = ProviderContainer();
    addTearDown(container.dispose);

    expect(container.read(themeModeControllerProvider), ThemeMode.system);
  });

  test('setThemeMode switches to light, dark, then back to system', () {
    final container = ProviderContainer();
    addTearDown(container.dispose);

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
}
