import 'package:assen_mobile/src/api/api_providers.dart';
import 'package:assen_mobile/src/settings/payment_method.dart';
import 'package:assen_mobile/src/settings/settings_repository.dart';
import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// Reads the signed-in fan's saved payment methods (`GET /api/fan/payment-methods`).
///
/// Read-only from the app for now: registering a method is a 대표·법무·PG gate
/// (the server's POST is fail-closed behind the tokenizer), so the 결제 수단 screen
/// lists existing methods and shows a "준비 중" notice instead of an add flow. A
/// thin repository over [Dio] owning the endpoint + JSON→model mapping; a 401
/// becomes a [SettingsAuthRequiredException] so the screen drops to the shared
/// "로그인이 필요해요" state. When the generated `api_client` (P6) lands, delegates.
class PaymentMethodsRepository {
  /// Creates a repository backed by [_dio].
  const PaymentMethodsRepository(this._dio);

  final Dio _dio;

  /// Loads the fan's saved methods via `GET /api/fan/payment-methods` (auth).
  ///
  /// The endpoint returns a *bare* JSON array (`list[PaymentMethodOut]`,
  /// newest first). A `null`/non-array body violates the contract and throws;
  /// only a real empty array `[]` means the fan has saved no method.
  Future<List<PaymentMethod>> fetchMethods() async {
    try {
      final response = await _dio.get<dynamic>('/api/fan/payment-methods');
      final data = response.data;
      if (data is! List) {
        throw ArgumentError(
          'GET /api/fan/payment-methods must return a JSON array '
          '(list[PaymentMethodOut])',
        );
      }
      return data
          .map((item) => PaymentMethod.fromJson(item as Map<String, dynamic>))
          .toList();
    } on DioException catch (error) {
      if (error.response?.statusCode == 401) {
        throw const SettingsAuthRequiredException();
      }
      rethrow;
    }
  }
}

/// Provides the [PaymentMethodsRepository] bound to the [dioProvider].
///
/// Overridden with a fake in widget tests so the 결제 수단 screen can render mock
/// methods (or the 401 branch) offline.
final paymentMethodsRepositoryProvider = Provider<PaymentMethodsRepository>(
  (ref) => PaymentMethodsRepository(ref.watch(dioProvider)),
);
