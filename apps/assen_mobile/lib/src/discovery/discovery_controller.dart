import 'package:assen_mobile/src/api/api_providers.dart';
import 'package:assen_mobile/src/discovery/creator.dart';
import 'package:assen_mobile/src/discovery/discovery_repository.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// Drives the discovery (home) feed's async lifecycle.
///
/// An [AsyncNotifier] so the screen renders loading/error/data from one value,
/// and can re-run the fetch via [refresh] (pull-to-refresh / retry) without the
/// screen owning any request state.
class DiscoveryController extends AsyncNotifier<List<Creator>> {
  @override
  Future<List<Creator>> build() {
    return ref.watch(discoveryRepositoryProvider).fetchCreators();
  }

  /// Re-fetches the feed, surfacing a fresh loading then data/error state.
  Future<void> refresh() async {
    state = const AsyncValue.loading();
    state = await AsyncValue.guard(
      () => ref.read(discoveryRepositoryProvider).fetchCreators(),
    );
  }
}

/// Exposes the discovery feed [AsyncValue] and its [DiscoveryController].
final discoveryControllerProvider =
    AsyncNotifierProvider<DiscoveryController, List<Creator>>(
      DiscoveryController.new,
      retry: noRetry,
    );
