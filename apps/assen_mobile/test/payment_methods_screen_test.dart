// Render tests for the 결제 수단 (payment methods) screen: a 401 shows the login
// prompt, an empty list shows the empty state + 준비 중 notice, and a loaded list
// renders each saved method's masked label (never a full PAN). Read-only — no
// add flow (PG gate). No network.

import 'package:assen_mobile/src/settings/payment_method.dart';
import 'package:assen_mobile/src/settings/payment_methods_repository.dart';
import 'package:assen_mobile/src/settings/payment_methods_screen.dart';
import 'package:assen_mobile/src/settings/settings_repository.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ui_kit/ui_kit.dart';

/// A repository stand-in: returns a fixed method list or the 401 error.
class _FakePaymentMethodsRepository implements PaymentMethodsRepository {
  _FakePaymentMethodsRepository(List<PaymentMethod> methods)
    : _methods = methods;
  _FakePaymentMethodsRepository.authRequired() : _methods = null;

  final List<PaymentMethod>? _methods;

  @override
  Future<List<PaymentMethod>> fetchMethods() async {
    final methods = _methods;
    if (methods == null) throw const SettingsAuthRequiredException();
    return methods;
  }
}

Widget _host(PaymentMethodsRepository repository) => ProviderScope(
  overrides: [paymentMethodsRepositoryProvider.overrideWithValue(repository)],
  child: MaterialApp(
    theme: AssenTheme.light(),
    home: const PaymentMethodsScreen(),
  ),
);

void main() {
  testWidgets('a 401 shows the login-required empty state', (tester) async {
    await tester.pumpWidget(
      _host(_FakePaymentMethodsRepository.authRequired()),
    );
    await tester.pump();
    await tester.pump();

    expect(find.text('로그인이 필요해요'), findsOneWidget);
  });

  testWidgets('an empty list shows the empty state and 준비 중 notice', (
    tester,
  ) async {
    await tester.pumpWidget(_host(_FakePaymentMethodsRepository(const [])));
    await tester.pump();
    await tester.pump();

    expect(find.text('저장된 결제 수단이 없어요'), findsOneWidget);
    expect(find.text('결제 수단 추가·변경은 준비 중이에요.'), findsOneWidget);
  });

  testWidgets('renders each saved method by its masked label', (tester) async {
    await tester.pumpWidget(
      _host(
        _FakePaymentMethodsRepository(const [
          PaymentMethod(
            id: 'm-1',
            brand: 'VISA',
            last4: '4242',
            isPrimary: true,
          ),
          PaymentMethod(
            id: 'm-2',
            brand: 'MASTER',
            last4: '5555',
            isPrimary: false,
          ),
        ]),
      ),
    );
    await tester.pump();
    await tester.pump();

    expect(find.text('VISA ····4242'), findsOneWidget);
    expect(find.text('MASTER ····5555'), findsOneWidget);
    expect(find.text('기본'), findsOneWidget); // the primary badge
  });
}
