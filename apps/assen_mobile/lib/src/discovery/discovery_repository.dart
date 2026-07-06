import 'package:assen_mobile/src/api/api_providers.dart';
import 'package:assen_mobile/src/discovery/creator.dart';
import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// Fetches the discovery (home) feed from the backend.
///
/// A thin repository over [Dio]: it owns the endpoint path and the JSON→model
/// mapping so the controller/UI stay transport-agnostic. When the generated
/// `api_client` (P6) lands, this method delegates to it instead of calling Dio
/// directly.
class DiscoveryRepository {
  /// Creates a repository backed by [_dio].
  const DiscoveryRepository(this._dio);

  final Dio _dio;

  /// Loads the creators shown on the discovery feed.
  ///
  /// Calls `GET /api/creators`, which returns a `CreatorPage` envelope
  /// (`{items: [...], next_cursor}`), and maps `items` into [Creator]s. A
  /// missing body or a missing `items` array is treated as an empty feed rather
  /// than an error. `next_cursor` carries the keyset cursor for the next page;
  /// consuming it (infinite scroll) is a follow-up (M5) — only the first page
  /// is read here.
  Future<List<Creator>> fetchCreators() async {
    final response = await _dio.get<Map<String, dynamic>>('/api/creators');
    final body = response.data ?? const <String, dynamic>{};
    final items = body['items'] as List<dynamic>? ?? const <dynamic>[];
    return items
        .map((item) => Creator.fromJson(item as Map<String, dynamic>))
        .toList();
  }
}

/// Provides the [DiscoveryRepository] bound to the configured [dioProvider].
///
/// Overridden with a fake in widget tests so the home screen can render mock
/// data without a network.
final discoveryRepositoryProvider = Provider<DiscoveryRepository>(
  (ref) => DiscoveryRepository(ref.watch(dioProvider)),
);
