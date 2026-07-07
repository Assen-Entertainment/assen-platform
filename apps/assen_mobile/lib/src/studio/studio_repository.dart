import 'package:assen_mobile/src/api/api_providers.dart';
import 'package:assen_mobile/src/studio/studio_stats.dart';
import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// Thrown when `GET /api/studio/stats` returns 401 (the caller is signed out).
///
/// A typed marker so the 스튜디오 screen can branch to the "로그인이 필요해요" state.
/// This is the common path today: the app ships signed-out, so the endpoint
/// (which requires `fan_auth`) answers 401 until real login lands (E6 gate).
class StudioAuthRequiredException implements Exception {
  /// Creates the auth-required marker.
  const StudioAuthRequiredException();

  @override
  String toString() => 'StudioAuthRequiredException';
}

/// Thrown when `GET /api/studio/stats` returns 403 (the caller operates no
/// creator).
///
/// A typed marker — distinct from [StudioAuthRequiredException] — so the screen
/// can branch to the dedicated "크리에이터 전용" state instead of the login prompt.
/// The server 403s (OwnerRequired) a signed-in fan who does not own a creator.
class StudioOwnerRequiredException implements Exception {
  /// Creates the owner-required marker.
  const StudioOwnerRequiredException();

  @override
  String toString() => 'StudioOwnerRequiredException';
}

/// Fetches the signed-in creator owner's studio dashboard counts.
///
/// A thin repository over [Dio] owning the endpoint path and the JSON→model
/// mapping so the controller/UI stay transport-agnostic. When the generated
/// `api_client` (P6) lands, this delegates to it instead of calling Dio.
class StudioRepository {
  /// Creates a repository backed by [_dio].
  const StudioRepository(this._dio);

  final Dio _dio;

  /// Loads the studio dashboard via `GET /api/studio/stats` (creator-owner).
  ///
  /// A 401 becomes a [StudioAuthRequiredException] (signed out) and a 403 a
  /// [StudioOwnerRequiredException] (signed in but not a creator) so
  /// the screen can render the two distinct states; other transport errors
  /// propagate to the generic error state. The 200 body is parsed strictly by
  /// [StudioStats.fromJson].
  Future<StudioStats> fetchStats() async {
    try {
      final response = await _dio.get<Map<String, dynamic>>(
        '/api/studio/stats',
      );
      return StudioStats.fromJson(response.data ?? const <String, dynamic>{});
    } on DioException catch (error) {
      final status = error.response?.statusCode;
      if (status == 401) throw const StudioAuthRequiredException();
      if (status == 403) throw const StudioOwnerRequiredException();
      rethrow;
    }
  }
}

/// Provides the [StudioRepository] bound to the configured [dioProvider].
///
/// Overridden with a fake in widget tests so the screen can render mock stats
/// (or the 401/403 branches) without a network.
final studioRepositoryProvider = Provider<StudioRepository>(
  (ref) => StudioRepository(ref.watch(dioProvider)),
);
