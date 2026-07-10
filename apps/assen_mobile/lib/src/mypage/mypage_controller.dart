import 'package:assen_mobile/src/api/api_providers.dart';
import 'package:assen_mobile/src/common/refreshable_async_notifier.dart';
import 'package:assen_mobile/src/mypage/fan_me.dart';
import 'package:assen_mobile/src/mypage/mypage_repository.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// Drives the 마이 tab's async lifecycle.
///
/// An [AsyncNotifier] so the screen renders loading/error/data from one value
/// and can re-run the fetch via [refresh] (retry). Only exercised while signed
/// in — the router redirects guests to the login wall before this builds.
class MyPageController extends AsyncNotifier<FanMe>
    with RefreshableAsyncNotifier<FanMe> {
  @override
  Future<FanMe> build() {
    return ref.watch(myPageRepositoryProvider).fetchMe();
  }

  @override
  Future<FanMe> fetch() => ref.read(myPageRepositoryProvider).fetchMe();
}

/// Exposes the fan identity [AsyncValue] and its [MyPageController].
final myPageControllerProvider = AsyncNotifierProvider<MyPageController, FanMe>(
  MyPageController.new,
  retry: noRetry,
);
