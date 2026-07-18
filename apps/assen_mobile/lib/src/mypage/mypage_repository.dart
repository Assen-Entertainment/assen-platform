import 'package:assen_mobile/src/api/api_providers.dart';
import 'package:assen_mobile/src/mypage/fan_me.dart';
import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// Fetches the authenticated fan's identity summary from the backend.
///
/// A thin repository over [Dio] owning the endpoint path and the JSON→model
/// mapping so the controller/UI stay transport-agnostic. When the generated
/// `api_client` (P6) lands, this delegates to it instead of calling Dio.
class MyPageRepository {
  /// Creates a repository backed by [_dio].
  const MyPageRepository(this._dio);

  final Dio _dio;

  /// Loads the fan's identity summary via `GET /api/fan/me` (auth required).
  ///
  /// The 마이 tab is only reached when signed in (the router redirects guests to
  /// the login wall), so the request is expected to carry a bearer token.
  Future<FanMe> fetchMe() async {
    final response = await _dio.get<Map<String, dynamic>>('/api/fan/me');
    return FanMe.fromJson(response.data ?? const <String, dynamic>{});
  }
}

/// Provides the [MyPageRepository] bound to the configured [dioProvider].
///
/// Overridden with a fake in widget tests so the screen can render a mock
/// identity without a network.
final myPageRepositoryProvider = Provider<MyPageRepository>(
  (ref) => MyPageRepository(ref.watch(dioProvider)),
);
