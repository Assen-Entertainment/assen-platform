import 'package:assen_mobile/src/api/api_providers.dart';
import 'package:assen_mobile/src/common/refreshable_async_notifier.dart';
import 'package:assen_mobile/src/settings/blocked_creator.dart';
import 'package:assen_mobile/src/settings/blocked_repository.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// Drives the 차단 관리 (blocked creators) screen's async lifecycle.
///
/// An [AsyncNotifier] so the screen renders loading/error/data from one value
/// and can re-run the fetch via [refresh]. [unblock] optimistically drops the
/// row and DELETEs, restoring it on failure. A signed-out caller surfaces as a
/// SettingsAuthRequiredException which the screen maps to the login wall.
class BlockedController extends AsyncNotifier<List<BlockedCreator>>
    with RefreshableAsyncNotifier<List<BlockedCreator>> {
  @override
  Future<List<BlockedCreator>> build() =>
      ref.watch(blockedRepositoryProvider).fetchBlocked();

  @override
  Future<List<BlockedCreator>> fetch() =>
      ref.read(blockedRepositoryProvider).fetchBlocked();

  /// Optimistically unblocks [creatorId], removing its row immediately.
  ///
  /// The row is dropped from the list first (so the tap feels instant), then
  /// the DELETE runs; on failure the prior list is restored and the error
  /// rethrown so the screen can surface it (a toast, or the login drop).
  Future<void> unblock(String creatorId) async {
    final current = state.value;
    if (current == null) return;
    state = AsyncValue.data(
      current.where((b) => b.creatorId != creatorId).toList(),
    );
    try {
      await ref.read(blockedRepositoryProvider).unblock(creatorId);
    } on Object {
      state = AsyncValue.data(current);
      rethrow;
    }
  }
}

/// Exposes the blocked-creators [AsyncValue] and its [BlockedController].
final blockedControllerProvider =
    AsyncNotifierProvider<BlockedController, List<BlockedCreator>>(
      BlockedController.new,
      retry: noRetry,
    );
