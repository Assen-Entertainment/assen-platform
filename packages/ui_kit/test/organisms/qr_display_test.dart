// Widget tests for AssenQrDisplay. Active vs. expired, brightness notice,
// countdown caption, and the expired refresh. Golden skip #31.

import 'package:alchemist/alchemist.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ui_kit/ui_kit.dart';

Widget _host(Widget child) => MaterialApp(
  theme: AssenTheme.light(),
  home: Scaffold(body: Center(child: child)),
);

void main() {
  group('AssenQrDisplay', () {
    testWidgets('active shows brightness notice and countdown', (tester) async {
      await tester.pumpWidget(
        _host(
          const AssenQrDisplay(
            memberNumber: '0000 1234 5678',
            remainingLabel: '29초',
            progress: 0.7,
          ),
        ),
      );
      expect(find.textContaining('밝기를 자동으로'), findsOneWidget);
      expect(find.text('29초 후 코드가 갱신됩니다'), findsOneWidget);
      // Active state draws the rotation timer ring.
      expect(find.byType(AssenProgressDonut), findsOneWidget);
    });

    testWidgets('expired masks the code and shows the refresh prompt', (
      tester,
    ) async {
      var refresh = 0;
      await tester.pumpWidget(
        _host(
          AssenQrDisplay(
            memberNumber: '0000 1234 5678',
            status: AssenQrStatus.expired,
            onRefresh: () => refresh++,
          ),
        ),
      );
      expect(find.text('코드가 만료되었습니다.'), findsOneWidget);
      // No rotation ring while expired.
      expect(find.byType(AssenProgressDonut), findsNothing);
      await tester.tap(find.text('코드 새로 고침'));
      expect(refresh, 1);
    });

    testWidgets('renders the membership number for manual fallback', (
      tester,
    ) async {
      await tester.pumpWidget(
        _host(
          const AssenQrDisplay(
            memberNumber: '0000 1234 5678',
            remainingLabel: '10초',
          ),
        ),
      );
      expect(find.text('0000 1234 5678'), findsOneWidget);
    });

    testWidgets('labels the QR container for screen readers', (tester) async {
      await tester.pumpWidget(
        _host(
          const AssenQrDisplay(
            memberNumber: '0000 1234 5678',
            remainingLabel: '10초',
          ),
        ),
      );
      final semantics = tester.widget<Semantics>(
        find
            .descendant(
              of: find.byType(AssenQrDisplay),
              matching: find.byType(Semantics),
            )
            .first,
      );
      expect(semantics.properties.label, contains('회원증 QR'));
      expect(semantics.container, isTrue);
    });
  });

  goldenTest(
    'qr display matches the approved baseline',
    fileName: 'qr_display',
    skip: true, // 베이스라인 인간 승인 대기 (#31)
    builder: () => GoldenTestGroup(
      children: [
        GoldenTestScenario(
          name: 'active',
          child: const SizedBox(
            width: 320,
            child: AssenQrDisplay(
              memberNumber: '0000 1234 5678',
              remainingLabel: '29초',
              progress: 0.72,
            ),
          ),
        ),
      ],
    ),
  );
}
