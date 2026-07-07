import 'package:assen_mobile/src/api/api_providers.dart';
import 'package:assen_mobile/src/membership/tier.dart';
import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// Fetches a creator's public membership tiers from the backend.
///
/// A thin repository over [Dio] owning the endpoint path and the JSON→model
/// mapping so the controller/UI stay transport-agnostic. When the generated
/// `api_client` (P6) lands, this delegates to it instead of calling Dio.
class MembershipRepository {
  /// Creates a repository backed by [_dio].
  const MembershipRepository(this._dio);

  final Dio _dio;

  /// Loads the active tiers for [creatorId] via `GET /api/tiers?creator_id=`.
  ///
  /// Unlike the feed/store envelopes this endpoint returns a *bare* JSON array
  /// (`list[TierOut]`, already sorted by the server), so the list is read
  /// directly. The body is parsed strictly: a `null`/non-array body is a
  /// contract violation and throws [ArgumentError] (consistent with the
  /// `requireList` envelopes) rather than silently hiding the section; only a
  /// real empty array `[]` means the creator offers no membership.
  Future<List<Tier>> fetchTiers(String creatorId) async {
    final response = await _dio.get<dynamic>(
      '/api/tiers',
      queryParameters: {'creator_id': creatorId},
    );
    final data = response.data;
    if (data is! List) {
      throw ArgumentError.value(
        data,
        'response.data',
        'GET /api/tiers must return a JSON array (bare list[TierOut])',
      );
    }
    return data
        .map((item) => Tier.fromJson(item as Map<String, dynamic>))
        .toList();
  }
}

/// Provides the [MembershipRepository] bound to the configured [dioProvider].
///
/// Overridden with a fake in widget tests so the membership section can render
/// mock tiers without a network.
final membershipRepositoryProvider = Provider<MembershipRepository>(
  (ref) => MembershipRepository(ref.watch(dioProvider)),
);
