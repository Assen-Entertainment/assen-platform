import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// Owns the app's [ThemeMode] choice (design review follow-up to ASS-282).
///
/// Defaults to [ThemeMode.system] — the same behaviour as the previous
/// hard-coded default in `AssenApp` — but now the fan can override it from the
/// 설정 screen (밝게/어둡게/시스템 설정) so an OS-dark device can still show the
/// light-forward brand identity (warm paper) when that is what the fan wants.
///
/// DEFERRED (persistence): the choice lives in memory only for now and resets
/// to [ThemeMode.system] on the next app launch. The workspace has no local
/// preference store yet — `flutter_secure_storage` is reserved for the auth
/// token pair only (see `TokenStore`'s doc: "the ONLY session material the app
/// persists"), and `shared_preferences` is not a workspace dependency. Wiring
/// this to `shared_preferences` (once added) is follow-up work; this provider
/// is written so that hookup only touches `build()`/`setThemeMode()` here.
class ThemeModeController extends Notifier<ThemeMode> {
  @override
  ThemeMode build() => ThemeMode.system;

  /// Switches the app to [mode] (light/dark/system).
  ///
  /// A verb-named method (not a setter) to match every other [Notifier]
  /// mutator in this codebase (`AuthController.signOut`,
  /// `SettingsController.updateNickname`, …).
  // ignore: use_setters_to_change_properties
  void setThemeMode(ThemeMode mode) => state = mode;
}

/// Exposes the current [ThemeMode] and its [ThemeModeController].
final themeModeControllerProvider =
    NotifierProvider<ThemeModeController, ThemeMode>(ThemeModeController.new);
