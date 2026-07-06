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
  /// Calls `GET /api/v1/creators` and maps the JSON array into [Creator]s. A
  /// missing body is treated as an empty feed rather than an error.
  Future<List<Creator>> fetchCreators() async {
    final response = await _dio.get<List<dynamic>>('/api/v1/creators');
    final data = response.data ?? const <dynamic>[];
    return data
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
