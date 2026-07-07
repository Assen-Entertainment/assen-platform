import 'package:assen_mobile/src/api/api_providers.dart';
import 'package:assen_mobile/src/mypage/fan_me.dart';
import 'package:assen_mobile/src/settings/settings_repository.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// Drives the 설정 screen's async lifecycle.
///
/// An [AsyncNotifier] so the screen renders loading/error/data from one value
/// and can re-run the fetch via [refresh] (retry). A signed-out caller surfaces
/// as a [SettingsAuthRequiredException] in the error state, which the screen
/// maps to the "로그인이 필요해요" branch rather than a failure.
class SettingsController extends AsyncNotifier<FanMe> {
  @override
  Future<FanMe> build() {
    return ref.watch(settingsRepositoryProvider).fetchMe();
  }

  /// Re-fetches the profile (fresh loading then data/error state).
  Future<void> refresh() async {
    state = const AsyncValue.loading();
    state = await AsyncValue.guard(
      () => ref.read(settingsRepositoryProvider).fetchMe(),
    );
  }

  /// Updates the nickname via PATCH and reflects the refreshed profile.
  ///
  /// On success the returned [FanMe] replaces the current state so the screen
  /// re-renders with the new nickname. Failures are rethrown so the caller (the
  /// editor) can surface them without clobbering the loaded profile.
  Future<void> updateNickname(String nickname) async {
    final updated = await ref
        .read(settingsRepositoryProvider)
        .updateNickname(nickname);
    state = AsyncValue.data(updated);
  }
}

/// Exposes the fan profile [AsyncValue] and its [SettingsController].
final settingsControllerProvider =
    AsyncNotifierProvider<SettingsController, FanMe>(
      SettingsController.new,
      retry: noRetry,
    );
