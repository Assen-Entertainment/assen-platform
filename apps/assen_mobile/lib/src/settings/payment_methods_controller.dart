import 'package:assen_mobile/src/api/api_providers.dart';
import 'package:assen_mobile/src/common/refreshable_async_notifier.dart';
import 'package:assen_mobile/src/settings/payment_method.dart';
import 'package:assen_mobile/src/settings/payment_methods_repository.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// Drives the 결제 수단 (payment methods) screen's async lifecycle.
///
/// An [AsyncNotifier] so the screen renders loading/error/data from one value
/// and can re-run the fetch via [refresh] (retry). A signed-out caller surfaces
/// as a SettingsAuthRequiredException which the screen maps to the login wall.
/// Read-only — adding a method is a PG gate, so there is no mutation here.
class PaymentMethodsController extends AsyncNotifier<List<PaymentMethod>>
    with RefreshableAsyncNotifier<List<PaymentMethod>> {
  @override
  Future<List<PaymentMethod>> build() =>
      ref.watch(paymentMethodsRepositoryProvider).fetchMethods();

  @override
  Future<List<PaymentMethod>> fetch() =>
      ref.read(paymentMethodsRepositoryProvider).fetchMethods();
}

/// Exposes the payment-methods [AsyncValue] and its [PaymentMethodsController].
final paymentMethodsControllerProvider =
    AsyncNotifierProvider<PaymentMethodsController, List<PaymentMethod>>(
      PaymentMethodsController.new,
      retry: noRetry,
    );
