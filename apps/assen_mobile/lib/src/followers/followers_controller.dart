import 'package:assen_mobile/src/api/api_providers.dart';
import 'package:assen_mobile/src/common/refreshable_async_notifier.dart';
import 'package:assen_mobile/src/followers/follower.dart';
import 'package:assen_mobile/src/followers/followers_repository.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
// The family provider type returned by `AsyncNotifierProvider.family` lives in
// riverpod's `misc` library, not the default export; it is imported here so the
// provider can carry the explicit type the workspace ruleset requires.
import 'package:flutter_riverpod/misc.dart' show AsyncNotifierProviderFamily;

/// Drives one creator's followers list, keyed by handle.
///
/// A family [AsyncNotifier] (one instance per handle) so the 팔로워 screen renders
/// loading/error/data from a single value and can re-run its fetch via [refresh]
/// (retry). The handle argument is delivered by the family (Riverpod 3.x) and
/// read back in [build]. An unknown handle surfaces as a
/// FollowersCreatorNotFoundException.
class FollowersController extends AsyncNotifier<List<Follower>>
    with RefreshableAsyncNotifier<List<Follower>> {
  /// Creates a controller for the creator identified by [handle].
  FollowersController(this.handle);

  /// The @-handle whose followers this controller loads.
  final String handle;

  @override
  Future<List<Follower>> build() =>
      ref.watch(followersRepositoryProvider).fetchFollowers(handle);

  @override
  Future<List<Follower>> fetch() =>
      ref.read(followersRepositoryProvider).fetchFollowers(handle);
}

/// Exposes each creator's followers [AsyncValue], keyed by handle.
final AsyncNotifierProviderFamily<FollowersController, List<Follower>, String>
followersControllerProvider =
    AsyncNotifierProvider.family<FollowersController, List<Follower>, String>(
      FollowersController.new,
      retry: noRetry,
    );
