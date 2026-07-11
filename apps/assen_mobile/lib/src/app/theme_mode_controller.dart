import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';

/// Owns the app's [ThemeMode] choice (design review follow-up to ASS-282).
///
/// Defaults to [ThemeMode.system] — the same behaviour as the previous
/// hard-coded default in `AssenApp` — but now the fan can override it from the
/// 설정 screen (밝게/어둡게/시스템 설정) so an OS-dark device can still show the
/// light-forward brand identity (warm paper) when that is what the fan wants.
///
/// The pick is persisted to [SharedPreferences] under [_prefsKey] (the enum
/// name, e.g. `"dark"`) so it survives the next app launch. `build()` must
/// return synchronously, so it hands back [ThemeMode.system] right away and
/// kicks off an async [_load] that applies any stored value once read — the
/// same restore-after-build shape as `AuthController._restore` (local storage
/// is inherently async here too). Fail-closed: a missing/unreadable/
/// unrecognized value just leaves the in-memory default in place.
class ThemeModeController extends Notifier<ThemeMode> {
  /// The local-storage key for the persisted mode (stores `ThemeMode.name`).
  static const String _prefsKey = 'assen.theme_mode';

  /// True once the fan has explicitly picked a mode this session, so a
  /// still-in-flight [_load] (from [build]) can never clobber that choice
  /// with a stale persisted value.
  bool _userSet = false;

  @override
  ThemeMode build() {
    unawaited(_load());
    return ThemeMode.system;
  }

  /// Restores a persisted mode, if any, once local storage resolves.
  Future<void> _load() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      if (_userSet) return; // the fan already picked a mode; don't clobber it
      final stored = prefs.getString(_prefsKey);
      state = ThemeMode.values.firstWhere(
        (mode) => mode.name == stored,
        orElse: () => ThemeMode.system,
      );
    } on Object {
      // Local storage unavailable/unreadable (e.g. no platform channel under
      // `flutter test`): keep the in-memory default.
    }
  }

  /// Switches the app to [mode] (light/dark/system) and persists the choice.
  ///
  /// A verb-named method (not a setter) to match every other [Notifier]
  /// mutator in this codebase (`AuthController.signOut`,
  /// `SettingsController.updateNickname`, …).
  void setThemeMode(ThemeMode mode) {
    _userSet = true;
    state = mode;
    unawaited(_persist(mode));
  }

  /// Best-effort write of [mode] to local storage.
  Future<void> _persist(ThemeMode mode) async {
    try {
      final prefs = await SharedPreferences.getInstance();
      await prefs.setString(_prefsKey, mode.name);
    } on Object {
      // Best-effort: the in-memory state already switched; a failed write
      // just means the choice won't survive the next launch.
    }
  }
}

/// Exposes the current [ThemeMode] and its [ThemeModeController].
final themeModeControllerProvider =
    NotifierProvider<ThemeModeController, ThemeMode>(ThemeModeController.new);
