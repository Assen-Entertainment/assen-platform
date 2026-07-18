import 'package:assen_mobile/src/api/api_providers.dart';
import 'package:assen_mobile/src/common/refreshable_async_notifier.dart';
import 'package:assen_mobile/src/mypage/fan_me.dart';
import 'package:assen_mobile/src/settings/settings_repository.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// Drives the 설정 screen's async lifecycle.
///
/// An [AsyncNotifier] so the screen renders loading/error/data from one value
/// and can re-run the fetch via [refresh] (retry). A signed-out caller surfaces
/// as a [SettingsAuthRequiredException] in the error state, which the screen
/// maps to the "로그인이 필요해요" branch rather than a failure.
class SettingsController extends AsyncNotifier<FanMe>
    with RefreshableAsyncNotifier<FanMe> {
  @override
  Future<FanMe> build() {
    return ref.watch(settingsRepositoryProvider).fetchMe();
  }

  @override
  Future<FanMe> fetch() => ref.read(settingsRepositoryProvider).fetchMe();

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

  /// Runs the (mock) 본인인증 and reflects the refreshed 인증 flags in the profile.
  ///
  /// Merges the derived `adult_verified`/`kyc_status` from the verify flow into
  /// the loaded profile so the settings badges update in place. Failures are
  /// rethrown so the KYC section can surface them (the "준비 중" notice for a 503,
  /// or the login-required drop for a 401) without clobbering the profile.
  Future<void> verifyAdult() async {
    final current = state.value;
    final result = await ref.read(settingsRepositoryProvider).verifyAdult();
    if (current == null) return;
    state = AsyncValue.data(
      FanMe(
        id: current.id,
        nickname: current.nickname,
        role: current.role,
        handle: current.handle,
        avatarUrl: current.avatarUrl,
        adultVerified: result.adultVerified,
        kycStatus: result.kycStatus,
      ),
    );
  }

  /// Drops the screen to the "로그인이 필요해요" state (session expired mid-edit).
  ///
  /// Called by the nickname editor when a save returns a
  /// [SettingsAuthRequiredException] so a stale, signed-out profile is not left
  /// on screen behind a generic error.
  void markAuthRequired() {
    state = AsyncValue.error(
      const SettingsAuthRequiredException(),
      StackTrace.current,
    );
  }
}

/// Exposes the fan profile [AsyncValue] and its [SettingsController].
final settingsControllerProvider =
    AsyncNotifierProvider<SettingsController, FanMe>(
      SettingsController.new,
      retry: noRetry,
    );
