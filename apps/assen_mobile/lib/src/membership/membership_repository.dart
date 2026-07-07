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
  /// directly. A null/absent body degrades to an empty tier list (the creator
  /// offers no membership) rather than an error.
  Future<List<Tier>> fetchTiers(String creatorId) async {
    final response = await _dio.get<List<dynamic>>(
      '/api/tiers',
      queryParameters: {'creator_id': creatorId},
    );
    final items = response.data ?? const <dynamic>[];
    return items
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
