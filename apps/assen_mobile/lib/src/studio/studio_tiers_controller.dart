import 'package:assen_mobile/src/api/api_providers.dart';
import 'package:assen_mobile/src/common/refreshable_async_notifier.dart';
import 'package:assen_mobile/src/studio/studio_tier.dart';
import 'package:assen_mobile/src/studio/studio_tiers_repository.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// Drives the 멤버십 관리 (studio tiers) screen's async lifecycle.
///
/// An [AsyncNotifier] so the screen renders loading/error/data from one value
/// and can re-run the fetch via [refresh] (retry). A signed-out caller surfaces
/// as a StudioAuthRequiredException, a signed-in non-owner as a
/// StudioOwnerRequiredException, which the screen maps to its two states.
class StudioTiersController extends AsyncNotifier<List<StudioTier>>
    with RefreshableAsyncNotifier<List<StudioTier>> {
  @override
  Future<List<StudioTier>> build() =>
      ref.watch(studioTiersRepositoryProvider).fetchTiers();

  @override
  Future<List<StudioTier>> fetch() =>
      ref.read(studioTiersRepositoryProvider).fetchTiers();
}

/// Exposes the owner's tiers [AsyncValue] and its controller.
final studioTiersControllerProvider =
    AsyncNotifierProvider<StudioTiersController, List<StudioTier>>(
      StudioTiersController.new,
      retry: noRetry,
    );
