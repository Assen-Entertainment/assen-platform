import 'package:assen_mobile/src/api/api_providers.dart';
import 'package:assen_mobile/src/settings/blocked_creator.dart';
import 'package:assen_mobile/src/settings/settings_repository.dart';
import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// Reads and mutates the signed-in fan's personal creator-block list.
///
/// A thin repository over [Dio] owning the `/api/fan/blocks` endpoints (GET list,
/// DELETE unblock) and the JSON→model mapping so the controller/UI stay
/// transport-agnostic. A 401/403 becomes a [SettingsAuthRequiredException] so the
/// 차단 관리 screen drops to the shared "로그인이 필요해요" state; other transport errors
/// propagate. When the generated `api_client` (P6) lands this delegates to it.
class BlockedRepository {
  /// Creates a repository backed by [_dio].
  const BlockedRepository(this._dio);

  final Dio _dio;

  /// Loads the fan's blocked creators via `GET /api/fan/blocks` (auth required).
  ///
  /// The endpoint returns a *bare* JSON array (`list[BlockedCreatorOut]`,
  /// newest first), so the list is read directly. A `null`/non-array body is a
  /// contract violation and throws rather than silently showing an empty list;
  /// only a real empty array `[]` means the fan has blocked no one.
  Future<List<BlockedCreator>> fetchBlocked() async {
    try {
      final response = await _dio.get<dynamic>('/api/fan/blocks');
      final data = response.data;
      if (data is! List) {
        throw ArgumentError(
          'GET /api/fan/blocks must return a JSON array (list[BlockedCreatorOut])',
        );
      }
      return data
          .map((item) => BlockedCreator.fromJson(item as Map<String, dynamic>))
          .toList();
    } on DioException catch (error) {
      if (error.response?.statusCode == 401) {
        throw const SettingsAuthRequiredException();
      }
      rethrow;
    }
  }

  /// Unblocks [creatorId] via `DELETE /api/fan/blocks/{creator_id}`.
  ///
  /// Idempotent on the server (unblocking a non-block is a no-op, still 200),
  /// so a retry after a flaky first attempt is safe.
  Future<void> unblock(String creatorId) async {
    try {
      await _dio.delete<dynamic>('/api/fan/blocks/$creatorId');
    } on DioException catch (error) {
      final status = error.response?.statusCode;
      if (status == 401 || status == 403) {
        throw const SettingsAuthRequiredException();
      }
      rethrow;
    }
  }
}

/// Provides the [BlockedRepository] bound to the configured [dioProvider].
///
/// Overridden with a fake in widget tests so the 차단 관리 screen can render a mock
/// list (or the 401 branch) and exercise unblock offline.
final blockedRepositoryProvider = Provider<BlockedRepository>(
  (ref) => BlockedRepository(ref.watch(dioProvider)),
);
