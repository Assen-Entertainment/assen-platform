import 'package:assen_mobile/src/api/api_providers.dart';
import 'package:assen_mobile/src/creator/creator_repository.dart';
import 'package:assen_mobile/src/discovery/creator.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
// The family provider type returned by `AsyncNotifierProvider.family` lives in
// riverpod's `misc` library, not the default export; it is imported here so the
// provider can carry the explicit type the workspace ruleset requires.
import 'package:flutter_riverpod/misc.dart' show AsyncNotifierProviderFamily;

/// Drives one creator profile's async lifecycle, keyed by handle.
///
/// A family [AsyncNotifier] (one instance per handle) so each profile renders
/// loading/error/data from a single value and can re-run its fetch via
/// [refresh] (retry) without the screen owning any request state. The handle
/// argument is delivered to the notifier by the family (Riverpod 3.x) and read
/// back in [build].
class CreatorController extends AsyncNotifier<Creator> {
  /// Creates a controller for the profile identified by [handle].
  CreatorController(this.handle);

  /// The @-handle whose profile this controller loads.
  final String handle;

  @override
  Future<Creator> build() {
    return ref.watch(creatorRepositoryProvider).fetchCreator(handle);
  }

  /// Re-fetches the profile, surfacing a fresh loading then data/error state.
  Future<void> refresh() async {
    state = const AsyncValue.loading();
    state = await AsyncValue.guard(
      () => ref.read(creatorRepositoryProvider).fetchCreator(handle),
    );
  }
}

/// Exposes each creator profile's [AsyncValue], keyed by handle.
final AsyncNotifierProviderFamily<CreatorController, Creator, String>
creatorControllerProvider =
    AsyncNotifierProvider.family<CreatorController, Creator, String>(
      CreatorController.new,
      retry: noRetry,
    );
