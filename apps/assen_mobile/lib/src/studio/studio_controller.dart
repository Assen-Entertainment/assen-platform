import 'package:assen_mobile/src/api/api_providers.dart';
import 'package:assen_mobile/src/studio/studio_repository.dart';
import 'package:assen_mobile/src/studio/studio_stats.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// Drives the 스튜디오 screen's async lifecycle.
///
/// An [AsyncNotifier] so the screen renders loading/error/data from one value
/// and can re-run the fetch via [refresh] (retry). A signed-out caller surfaces
/// as a [StudioAuthRequiredException] and a non-creator as a
/// [StudioOwnerRequiredException] in the error state, which the screen maps to
/// two distinct branches rather than a generic failure.
class StudioController extends AsyncNotifier<StudioStats> {
  @override
  Future<StudioStats> build() {
    return ref.watch(studioRepositoryProvider).fetchStats();
  }

  /// Re-fetches the dashboard, surfacing a fresh loading then data/error state.
  Future<void> refresh() async {
    state = const AsyncValue.loading();
    state = await AsyncValue.guard(
      () => ref.read(studioRepositoryProvider).fetchStats(),
    );
  }
}

/// Exposes the studio dashboard [AsyncValue] and its [StudioController].
final studioControllerProvider =
    AsyncNotifierProvider<StudioController, StudioStats>(
      StudioController.new,
      retry: noRetry,
    );
