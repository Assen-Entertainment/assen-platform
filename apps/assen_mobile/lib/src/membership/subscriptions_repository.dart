import 'package:assen_mobile/src/api/api_providers.dart';
import 'package:assen_mobile/src/membership/subscription.dart';
import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// Thrown when `GET /api/subscriptions` returns 401 (the caller is signed out).
///
/// A typed marker so the 내 구독 screen can branch to the "로그인이 필요해요" state
/// rather than the generic retry error. The app ships signed-out, so the
/// endpoint (which requires `fan_auth`) answers 401 until real login lands.
class SubscriptionsAuthRequiredException implements Exception {
  /// Creates the auth-required marker.
  const SubscriptionsAuthRequiredException();

  @override
  String toString() => 'SubscriptionsAuthRequiredException';
}

/// Fetches the signed-in fan's own membership subscriptions.
///
/// A thin repository over [Dio] owning the `/api/subscriptions` endpoint and the
/// JSON→model mapping so the controller/UI stay transport-agnostic. This is a
/// READ surface — subscribe/cancel/change-tier are payment gates and are not
/// wired here. When the generated `api_client` (P6) lands this delegates to it.
class SubscriptionsRepository {
  /// Creates a repository backed by [_dio].
  const SubscriptionsRepository(this._dio);

  final Dio _dio;

  /// Loads the fan's subscriptions via `GET /api/subscriptions` (auth required).
  ///
  /// The endpoint returns a *bare* JSON array (`list[SubscriptionOut]`). A
  /// `null`/non-array body is a contract violation and throws; only a real empty
  /// array `[]` means the fan has no membership. A 401 becomes a
  /// [SubscriptionsAuthRequiredException]; other transport errors propagate.
  Future<List<Subscription>> fetchSubscriptions() async {
    try {
      final response = await _dio.get<dynamic>('/api/subscriptions');
      final data = response.data;
      if (data is! List) {
        throw ArgumentError(
          'GET /api/subscriptions must return a JSON array '
          '(list[SubscriptionOut])',
        );
      }
      return data
          .map((item) => Subscription.fromJson(item as Map<String, dynamic>))
          .toList();
    } on DioException catch (error) {
      if (error.response?.statusCode == 401) {
        throw const SubscriptionsAuthRequiredException();
      }
      rethrow;
    }
  }
}

/// Provides the [SubscriptionsRepository] bound to the [dioProvider].
///
/// Overridden with a fake in widget tests so the 내 구독 screen can render mock
/// subscriptions (or the 401 branch) without a network.
final subscriptionsRepositoryProvider = Provider<SubscriptionsRepository>(
  (ref) => SubscriptionsRepository(ref.watch(dioProvider)),
);
