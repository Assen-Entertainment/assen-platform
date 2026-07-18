import 'package:assen_mobile/src/api/api_providers.dart';
import 'package:assen_mobile/src/common/refreshable_async_notifier.dart';
import 'package:assen_mobile/src/membership/subscription.dart';
import 'package:assen_mobile/src/membership/subscriptions_repository.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// Drives the 내 구독 (subscriptions) screen's async lifecycle.
///
/// An [AsyncNotifier] so the screen renders loading/error/data from one value
/// and can re-run the fetch via [refresh] (retry). A signed-out caller surfaces
/// as a SubscriptionsAuthRequiredException, which the screen maps to the
/// "로그인이 필요해요" branch rather than a failure.
class SubscriptionsController extends AsyncNotifier<List<Subscription>>
    with RefreshableAsyncNotifier<List<Subscription>> {
  @override
  Future<List<Subscription>> build() =>
      ref.watch(subscriptionsRepositoryProvider).fetchSubscriptions();

  @override
  Future<List<Subscription>> fetch() =>
      ref.read(subscriptionsRepositoryProvider).fetchSubscriptions();
}

/// Exposes the fan's subscriptions [AsyncValue] and its controller.
final subscriptionsControllerProvider =
    AsyncNotifierProvider<SubscriptionsController, List<Subscription>>(
      SubscriptionsController.new,
      retry: noRetry,
    );
