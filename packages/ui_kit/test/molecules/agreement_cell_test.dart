// Widget tests for AssenAgreementCell (전체동의 / [필수] / [선택]) — Korean B2C
// convention #3. The all row hides the tag/chevron; individual rows show the
// [필수]/[선택] tag and a 전문 chevron. Golden skip #31.

import 'package:alchemist/alchemist.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ui_kit/ui_kit.dart';

Widget _host(Widget child) => MaterialApp(
  theme: AssenTheme.light(),
  home: Scaffold(body: child),
);

void main() {
  group('AssenAgreementCell', () {
    testWidgets('toggles via onChanged on tap', (tester) async {
      bool? next;
      await tester.pumpWidget(
        _host(
          AssenAgreementCell(
            label: '약관 동의',
            value: false,
            onChanged: (v) => next = v,
          ),
        ),
      );
      await tester.tap(find.text('약관 동의'));
      expect(next, isTrue);
    });

    testWidgets('shows the [필수] tag for required rows', (tester) async {
      await tester.pumpWidget(
        _host(
          AssenAgreementCell(
            label: '필수 약관',
            value: true,
            onChanged: (_) {},
          ),
        ),
      );
      expect(find.text('[필수]'), findsOneWidget);
    });

    testWidgets('shows the [선택] tag for optional rows', (tester) async {
      await tester.pumpWidget(
        _host(
          AssenAgreementCell(
            label: '선택 약관',
            kind: AssenAgreementKind.optional,
            value: false,
            onChanged: (_) {},
          ),
        ),
      );
      expect(find.text('[선택]'), findsOneWidget);
    });

    testWidgets('the master (all) row shows no tag', (tester) async {
      await tester.pumpWidget(
        _host(
          AssenAgreementCell(
            label: '전체 동의',
            kind: AssenAgreementKind.all,
            value: false,
            onChanged: (_) {},
          ),
        ),
      );
      expect(find.text('[필수]'), findsNothing);
      expect(find.text('[선택]'), findsNothing);
    });

    testWidgets('opens the terms via the chevron', (tester) async {
      var viewed = false;
      await tester.pumpWidget(
        _host(
          AssenAgreementCell(
            label: '약관',
            value: true,
            onChanged: (_) {},
            onViewTerms: () => viewed = true,
          ),
        ),
      );
      await tester.tap(find.byIcon(Icons.chevron_right));
      expect(viewed, isTrue);
    });
  });

  goldenTest(
    'agreement cell matches the approved baseline',
    fileName: 'agreement_cell',
    skip: true, // 베이스라인 인간 승인 대기 (#31)
    builder: () => GoldenTestGroup(
      children: [
        GoldenTestScenario(
          name: 'required',
          child: SizedBox(
            width: 320,
            child: AssenAgreementCell(
              label: '서비스 이용약관 동의',
              value: true,
              onChanged: (_) {},
              onViewTerms: () {},
            ),
          ),
        ),
      ],
    ),
  );
}
