import 'package:assen_mobile/src/api/api_providers.dart';
import 'package:assen_mobile/src/discovery/creator.dart';
import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// Thrown when `GET /api/creators/{handle}` returns 404 (unknown handle).
///
/// A typed marker (not a generic error) so the profile screen can render the
/// dedicated "없는 크리에이터" state instead of the generic retry error.
class CreatorNotFoundException implements Exception {
  /// Creates the not-found marker for [handle].
  const CreatorNotFoundException(this.handle);

  /// The handle that did not resolve.
  final String handle;

  @override
  String toString() => 'CreatorNotFoundException($handle)';
}

/// Fetches a single creator profile from the backend.
///
/// A thin repository over [Dio] owning the endpoint path and the JSON→model
/// mapping so the controller/UI stay transport-agnostic. When the generated
/// `api_client` (P6) lands, this delegates to it instead of calling Dio.
class CreatorRepository {
  /// Creates a repository backed by [_dio].
  const CreatorRepository(this._dio);

  final Dio _dio;

  /// Loads the public creator profile for [handle].
  ///
  /// Calls `GET /api/creators/{handle}` and maps the `CreatorOut` body into a
  /// [Creator]. A 404 is translated into a [CreatorNotFoundException] so the
  /// screen shows the "unknown creator" state; other transport errors propagate
  /// to the generic error state.
  Future<Creator> fetchCreator(String handle) async {
    try {
      final response = await _dio.get<Map<String, dynamic>>(
        '/api/creators/${Uri.encodeComponent(handle)}',
      );
      return Creator.fromJson(response.data ?? const <String, dynamic>{});
    } on DioException catch (error) {
      if (error.response?.statusCode == 404) {
        throw CreatorNotFoundException(handle);
      }
      rethrow;
    }
  }
}

/// Provides the [CreatorRepository] bound to the configured [dioProvider].
///
/// Overridden with a fake in widget tests so the profile screen can render mock
/// data without a network.
final creatorRepositoryProvider = Provider<CreatorRepository>(
  (ref) => CreatorRepository(ref.watch(dioProvider)),
);
