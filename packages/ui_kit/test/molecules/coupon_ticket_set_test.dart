// Widget tests for AssenCouponTicketSet (사용가능 / 사용완료). Renders title/validity
// and a redeem stub; used coupons show 사용완료 and ignore taps. Golden skip #31.

import 'package:alchemist/alchemist.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ui_kit/ui_kit.dart';

Widget _host(Widget child) => MaterialApp(
  theme: AssenTheme.light(),
  home: Scaffold(
    body: Center(child: SizedBox(width: 320, child: child)),
  ),
);

void main() {
  group('AssenCouponTicketSet', () {
    testWidgets('renders title, validity and stub', (tester) async {
      await tester.pumpWidget(
        _host(
          const AssenCouponTicketSet(
            title: '디저트 1+1',
            validity: '~2026.07.31 까지',
          ),
        ),
      );
      expect(find.text('디저트 1+1'), findsOneWidget);
      expect(find.text('~2026.07.31 까지'), findsOneWidget);
      expect(find.text('사용하기'), findsOneWidget);
    });

    testWidgets('fires onRedeem when available', (tester) async {
      var redeemed = false;
      await tester.pumpWidget(
        _host(
          AssenCouponTicketSet(
            title: '디저트 1+1',
            validity: '~2026.07.31',
            onRedeem: () => redeemed = true,
          ),
        ),
      );
      await tester.tap(find.text('사용하기'));
      expect(redeemed, isTrue);
    });

    testWidgets('used coupon shows 사용완료, not the stub', (tester) async {
      await tester.pumpWidget(
        _host(
          const AssenCouponTicketSet(
            title: '웰컴 음료',
            validity: '2026.05.01 사용',
            state: AssenCouponState.used,
          ),
        ),
      );
      expect(find.text('사용완료'), findsOneWidget);
      expect(find.text('사용하기'), findsNothing);
    });
  });

  goldenTest(
    'coupon ticket set matches the approved baseline',
    fileName: 'coupon_ticket_set',
    skip: true, // 베이스라인 인간 승인 대기 (#31)
    builder: () => GoldenTestGroup(
      children: [
        GoldenTestScenario(
          name: 'available',
          child: const SizedBox(
            width: 320,
            child: AssenCouponTicketSet(
              title: '디저트 1+1',
              subtitle: '음료 주문 시',
              validity: '~2026.07.31 까지',
            ),
          ),
        ),
      ],
    ),
  );
}
