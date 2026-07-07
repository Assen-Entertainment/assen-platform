import 'package:assen_mobile/src/api/api_providers.dart';
import 'package:assen_mobile/src/membership/membership_repository.dart';
import 'package:assen_mobile/src/membership/tier.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
// The family provider type returned by `AsyncNotifierProvider.family` lives in
// riverpod's `misc` library, not the default export; it is imported here so the
// provider can carry the explicit type the workspace ruleset requires.
import 'package:flutter_riverpod/misc.dart' show AsyncNotifierProviderFamily;

/// Drives one creator's membership tiers, keyed by creator id.
///
/// A family [AsyncNotifier] (one instance per creator) so the membership
/// section renders loading/error/data from a single value and can re-run its
/// fetch via
/// [refresh] (retry). The creator-id argument is delivered to the notifier by
/// the family (Riverpod 3.x) and read back in [build].
class MembershipController extends AsyncNotifier<List<Tier>> {
  /// Creates a controller for the creator identified by [creatorId].
  MembershipController(this.creatorId);

  /// The creator id whose tiers this controller loads.
  final String creatorId;

  @override
  Future<List<Tier>> build() {
    return ref.watch(membershipRepositoryProvider).fetchTiers(creatorId);
  }

  /// Re-fetches the tiers, surfacing a fresh loading then data/error state.
  Future<void> refresh() async {
    state = const AsyncValue.loading();
    state = await AsyncValue.guard(
      () => ref.read(membershipRepositoryProvider).fetchTiers(creatorId),
    );
  }
}

/// Exposes each creator's membership tiers [AsyncValue], keyed by creator id.
final AsyncNotifierProviderFamily<MembershipController, List<Tier>, String>
membershipControllerProvider =
    AsyncNotifierProvider.family<MembershipController, List<Tier>, String>(
      MembershipController.new,
      retry: noRetry,
    );
