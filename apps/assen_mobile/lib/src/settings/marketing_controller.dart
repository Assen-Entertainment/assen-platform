import 'package:assen_mobile/src/api/api_providers.dart';
import 'package:assen_mobile/src/common/refreshable_async_notifier.dart';
import 'package:assen_mobile/src/settings/marketing_consent.dart';
import 'package:assen_mobile/src/settings/marketing_repository.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// The three marketing channels the fan can opt in/out of.
enum MarketingChannel {
  /// 앱 푸시 알림 marketing.
  push,

  /// SMS(문자) marketing.
  sms,

  /// Email marketing (not collected yet — UI-disabled).
  email,
}

/// Drives the 알림 설정 (marketing consent) screen's async lifecycle.
///
/// An [AsyncNotifier] so the screen renders loading/error/data from one value
/// and can re-run the fetch via [refresh]. [setChannel] optimistically flips
/// one channel and PUTs the full state, reverting on failure so a failed save
/// never leaves the toggle showing an un-persisted value. A signed-out caller
/// surfaces as a SettingsAuthRequiredException which the screen maps to login.
class MarketingController extends AsyncNotifier<MarketingConsent>
    with RefreshableAsyncNotifier<MarketingConsent> {
  @override
  Future<MarketingConsent> build() =>
      ref.watch(marketingRepositoryProvider).fetchConsent();

  @override
  Future<MarketingConsent> fetch() =>
      ref.read(marketingRepositoryProvider).fetchConsent();

  /// Optimistically toggles [channel] to [enabled] and persists the full state.
  ///
  /// Applies the change locally first (so the switch responds instantly), then
  /// PUTs the complete consent; on success the server-confirmed state replaces
  /// it, on failure the prior state is restored and the error rethrown so the
  /// screen can surface it (a toast, or the login drop for an auth error).
  Future<void> setChannel(
    MarketingChannel channel, {
    required bool enabled,
  }) async {
    final current = state.value;
    if (current == null) return;
    final desired = switch (channel) {
      MarketingChannel.push => current.copyWith(push: enabled),
      MarketingChannel.sms => current.copyWith(sms: enabled),
      MarketingChannel.email => current.copyWith(email: enabled),
    };
    state = AsyncValue.data(desired);
    try {
      final saved = await ref
          .read(marketingRepositoryProvider)
          .saveConsent(desired);
      state = AsyncValue.data(saved);
    } on Object {
      // Roll back the optimistic flip so the toggle never shows a value that
      // did not persist; rethrow so the screen surfaces the failure.
      state = AsyncValue.data(current);
      rethrow;
    }
  }
}

/// Exposes the marketing consent [AsyncValue] and its [MarketingController].
final marketingControllerProvider =
    AsyncNotifierProvider<MarketingController, MarketingConsent>(
      MarketingController.new,
      retry: noRetry,
    );
